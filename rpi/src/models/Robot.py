import logging
import threading
import time
import asyncio

from .Command import CommandManager
from .PathFollowing import PathManager
from .Communication import LidarReader, SerialManager, SocketManager, EmitManager
from .Bus import EventBus
from .StateEstimation import StateEstimator
from .SensorData import SensorDataManager, Deskewer, ScanMatcher
from .Mapping import WorldModel
from .Manual import ManualManager
from . import RobotConfig, Mode, LoopMonitoring, ConfigManager, StateManager, ROBOT_CONFIG
from ..ai.get_commands import text_to_command
from socketio import AsyncClient as Socket


class Robot:
    def __init__(self, serial_manager: SerialManager, socketio):
        self.bus = EventBus()
        
        self.socketio: Socket = socketio
        self.serial: SerialManager = serial_manager
        self.state_estimator: StateEstimator = StateEstimator(self.bus)
        self.deskewer: Deskewer = Deskewer(self.state_estimator)
        self.loop_monitoring = LoopMonitoring()
        self.command_manager = CommandManager(self.serial)
        self.config_manager = ConfigManager(self.command_manager)
        self.state_manager = StateManager(self.command_manager, self.bus)
        self.world_model = WorldModel(self.state_manager)
        self.sensor_data_manager = SensorDataManager(self.state_manager, self.command_manager)
        self.manual_manager = ManualManager(self.command_manager, self.state_manager)
        self.socket_manager = SocketManager(self.socketio, self.state_manager, self.config_manager, self.manual_manager, self.world_model, self.bus)
        self.path_manager = PathManager(self.command_manager, self.world_model, self.state_manager, self.bus)
        self.emit_manager = EmitManager(self.socket_manager, self.state_manager, self.manual_manager, self.loop_monitoring)
        self.scan_matcher = ScanMatcher(self.world_model)
        
        self.latest_scan = None
        self.running: bool = False
        self.lifecycle_lock = threading.Lock()
        self._logger: logging.Logger = logging.getLogger("Robot")
        
        self.lidar_read_task: asyncio.Task | None = None
        self.main_loop_task: asyncio.Task | None = None
        self.main_loop_thread: threading.Thread | None = None  # Includes both main loop and lidar read loop
        self.loop: asyncio.AbstractEventLoop | None = None
        self._loop_ready: threading.Event = threading.Event()

    def _run_loop_thread(self):
        asyncio.set_event_loop(asyncio.new_event_loop())
        self.loop = asyncio.get_event_loop()
        self.main_loop_task = self.loop.create_task(self.start_loops())
        
        # Run lidar read loop
        lidar_reader = LidarReader(port="/dev/ttyUSB0", baudrate=460800)
        self.lidar_read_task = self.loop.create_task(lidar_reader.scan_loop(callback=self.sensor_data_manager.process_lidar_data))
        
        self._loop_ready.set()
        
        try:
            self.loop.run_until_complete(self.main_loop_task)
        except asyncio.CancelledError:
            pass
        finally:
            pending = asyncio.all_tasks(self.loop)
            for task in pending:
                task.cancel()
            if pending:
                self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            self.loop.close()

    def start(self):
        """Start the robot main loop on its own thread/asyncio loop."""
        with self.lifecycle_lock:
            if self.running:
                return
            
            self.running = True
            self.main_loop_thread = threading.Thread(target=self._run_loop_thread, name="RobotMainLoop", daemon=True)
            self.main_loop_thread.start()
        self._loop_ready.wait(timeout=2.0)
        self._logger.info("Robot main loop started")

    def stop(self):
        """Stop the robot main loop thread."""
        with self.lifecycle_lock:
            self.running = False
            loop = self.loop
            main_loop_task = self.main_loop_task
            main_loop_thread = self.main_loop_thread

        if loop and main_loop_task:
            loop.call_soon_threadsafe(main_loop_task.cancel)
        if main_loop_thread and main_loop_thread.is_alive():
            main_loop_thread.join(timeout=2.0)
        self._logger.info("Robot main loop stopped")

    async def run_on_robot_loop(self, coro):
        """Execute a robot coroutine on the robot's dedicated loop from another loop/thread."""
        if self.loop is None:
            raise RuntimeError("Robot loop is not running")
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return await asyncio.wrap_future(future)
        
    async def process_sensor_queue(self):
        sensor_data = self.sensor_data_manager.sensor_queue.get()
        if await self.state_manager.get_state() == Mode.STOPPED: # Only update state estimator if not stopped
            return sensor_data
        
        previous_sensor_data = await self.sensor_data_manager.get_previous_sensor_data()
        await self.state_estimator.update(sensor_data, previous_sensor_data)

        # Update EKF with missed packets
        await self.sensor_data_manager.set_previous_sensor_data(sensor_data)
        while not self.sensor_data_manager.sensor_queue.empty():
            sensor_data = self.sensor_data_manager.sensor_queue.get()
            previous_sensor_data = await self.sensor_data_manager.get_previous_sensor_data()
            await self.state_estimator.update(sensor_data, previous_sensor_data)
            await self.sensor_data_manager.set_previous_sensor_data(sensor_data)

        return sensor_data

    async def process_lidar_queue(self):
        latest_scan = None
    
        while not self.sensor_data_manager.lidar_queue.empty():
            latest_scan = self.sensor_data_manager.lidar_queue.get()
            data = await self.deskewer.deskew(latest_scan)
            
            if not data: 
                break
                
            point_cloud, reference_pose = data
            latest_scan = point_cloud  
            
            if await self.state_manager.get_state() != Mode.STOPPED and ROBOT_CONFIG.USE_LIDAR: # Only update the world model if not stopped
                best_pose, score = await self.scan_matcher.match(point_cloud, reference_pose)
                
                await self.state_estimator.apply_lidar_pose_correction(best_pose)
                
                await self.world_model.update(
                    point_cloud
                )
        
        if latest_scan: await self.sensor_data_manager.set_previous_lidar_data(latest_scan)
        
    async def ekf_loop(self):
        dt = 1 / ROBOT_CONFIG.EKF_FREQ
        while self.running:
            start = time.monotonic()

            data_available = await self.sensor_data_manager.enforce_timeouts(start)

            if not data_available:
                continue

            sensor_data = await self.process_sensor_queue()
            await self.sensor_data_manager.sync_with_embedded(sensor_data) # Syncs rpi state to embedded state
            self.loop_monitoring.update_loop_time(start)
            elapsed = time.monotonic() - start
            await asyncio.sleep(max(0.0001, dt - elapsed)) # 200Hz loop

        self._logger.info("Exited main loop")
        
    async def mapping_loop(self):
        dt = 1 / ROBOT_CONFIG.MAPPING_FREQ

        while self.running:
            start = time.monotonic()
            await self.process_lidar_queue()
            await self.world_model.decay_live_layer()

            elapsed = time.monotonic() - start
            await asyncio.sleep(max(0.0001, dt - elapsed)) # 200Hz loop

        await self.world_model.shutdown()
        self._logger.info("Exited mapping loop")
        
    async def path_manual_loop(self):
        dt = 1 / ROBOT_CONFIG.PATH_FOLLOWING_FREQ
        
        while self.running:
            start = time.monotonic()
            
            robot_state = await self.state_estimator.get_state_snapshot()
            await self.path_manager.execute_cur_path(robot_state) # Follows the current path if available
            await self.manual_manager.execute_manual_commands() # Executes manual commands such as joystick or custom velocity profiles
            
            elapsed = time.monotonic() - start
            await asyncio.sleep(max(0.0001, dt - elapsed))
            
        self._logger.info("Exited path following / manual control loop")
        
    async def emit_loop(self):
        dt = 1 / ROBOT_CONFIG.EMIT_SENSOR_FREQ
        
        while self.running:
            start = time.monotonic()

            previous_sensor_data, previous_lidar_data = await self.sensor_data_manager.get_previous_data_snapshot()
            robot_state = await self.state_estimator.get_state_snapshot()
            await self.emit_manager.send_sensor_update(previous_sensor_data, robot_state, previous_lidar_data)
            await self.emit_manager.send_map_update()

            elapsed = time.monotonic() - start
            await asyncio.sleep(max(0.0001, dt - elapsed))
            
        self._logger.info("Exited emit loop")
            
        
    async def start_loops(self):
        """Main loop to continuously read sensor data and update state estimator."""
        await self.config_manager.init()
        
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self.ekf_loop())
            tg.create_task(self.mapping_loop())
            tg.create_task(self.path_manual_loop())
            tg.create_task(self.emit_loop())
