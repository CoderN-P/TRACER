import logging
import threading
import math
import time
import struct
from collections import deque
import asyncio
from . import SerialManager, SensorData, Command, CommandType, LCDCommand, StateEstimator, Mode, ROBOT_CONFIG, MagnetometerData, MetaMode, Path, PurePursuit, LidarData
from .PathFollowing import GoToGoal
from ..ai.get_commands import text_to_command
from socketio import AsyncClient as Socket


class Robot:
    def __init__(self, serial_manager: SerialManager, socketio):
        self.serial: SerialManager = serial_manager
        self.last_emit_time: float = 0.0
        self.last_obstacle_detect_time: float = 0.0  # Last time ultrasonic data was processed for obstacle detection
 
        self.socketio: Socket = socketio
        self.running: bool = False
        self.left_distance_history: deque = deque(maxlen=10)  # Store last 10 distance readings for smoothing
        self.right_distance_history: deque = deque(maxlen=10)
        
        self.obstacle_clear: asyncio.Event = asyncio.Event()
        self.backup_time = 2
        self._logger: logging.Logger = logging.getLogger("RobotManager")
        self.motor_lock: asyncio.Lock = asyncio.Lock()
        self.state_estimator: StateEstimator = StateEstimator(self._logger)
        
        self.state: Mode = Mode.MANUAL
        self.meta_state: MetaMode = MetaMode.USER 
        self.state_lock: asyncio.Lock = asyncio.Lock()  # Lock to protect access to the robot's state (manual, autonomous, stopped)
        self.lidar_lock: asyncio.Lock = asyncio.Lock()   # Lock to protect access to lidar data (written and read by both socketio server and main loop)

        self.sensor_lock: threading.Lock = threading.Lock()          # shared between serial thread and asyncio
        self.previous_sensor_data: SensorData | None = None             # for any processing that needs to compare current and previous sensor data, only accessed within main loop
        self.latest_sensor_data: SensorData | None = None               # written by serial thread, read by pose loop
        self.lidar_data: LidarData | None = None
        self.repulsive_vector: tuple[float, float] = (0, 0) # repulsive vector calculated from lidar data for obstacle avoidance, updated in main loop after processing new lidar data, and used in path following to modify the target point for obstacle avoidance
        self.main_loop_task: asyncio.Task = None
        self.main_loop_thread: threading.Thread | None = None
        self.loop = None
        self._loop_ready: threading.Event = threading.Event()
     
        self.cur_path: Path | PurePursuit | GoToGoal | None = None 
        self.last_sensor_receive_time: float = time.monotonic()
        self.last_command_sent_at: float = 0.0
        self.last_command_type: CommandType | None = None
        self.last_command_id: str = ""
        self.freeze_after_cmd_window_s = 0.5
        
        self.obstacle_clear.set()

    async def send_safe_command(self, command: Command, wait_after: float = 0):
        async with self.motor_lock:
            now = asyncio.get_event_loop().time()
            self.last_command_sent_at = now
            self.last_command_type = command.command_type.name if hasattr(command.command_type, "name") else str(command.command_type)
            self.last_command_id = command.ID
            self.serial.send(command)
            if wait_after > 0:
                await asyncio.sleep(wait_after)

    def _run_loop_thread(self):
        asyncio.set_event_loop(asyncio.new_event_loop())
        self.loop = asyncio.get_event_loop()
        self.main_loop_task = self.loop.create_task(self.main_loop())
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
        if self.running:
            return
        self.running = True
        self.main_loop_thread = threading.Thread(target=self._run_loop_thread, name="RobotMainLoop", daemon=True)
        self.main_loop_thread.start()
        self._loop_ready.wait(timeout=2.0)
        self._logger.info("Robot main loop started")

    def stop(self):
        """Stop the robot main loop thread."""
        self.running = False
        if self.loop and self.main_loop_task:
            self.loop.call_soon_threadsafe(self.main_loop_task.cancel)
        if self.main_loop_thread and self.main_loop_thread.is_alive():
            self.main_loop_thread.join(timeout=2.0)
        self._logger.info("Robot main loop stopped")

    async def run_on_robot_loop(self, coro):
        """Execute a robot coroutine on the robot's dedicated loop from another loop/thread."""
        if self.loop is None:
            raise RuntimeError("Robot loop is not running")
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return await asyncio.wrap_future(future)
        
    async def _reset_obstacle_clear(self):
        await asyncio.sleep(ROBOT_CONFIG.BACKUP_TIME)  # Wait for backup duration before allowing new obstacle detection
        self.obstacle_clear.set()
        
    async def emergency_stop(self):
        """Immediately stop the robot and clear any pending commands."""
        await self.send_safe_command(Command.estop())
        self._logger.info("Stopping robot")
        async with self.state_lock:
            self.state = Mode.STOPPED
            
        await self.socketio.emit('emergency_stop', {"status": "success"})
        
        
    async def resume(self):
        """Resume normal operation after an emergency stop."""
        self._logger.info("Re-enabling robot")
        async with self.state_lock:
            self.state = Mode.MANUAL
        await self.send_safe_command(Command.stop())   # clear any stale setpoint
        await self.send_safe_command(Command.enable())
        self.state_estimator.reset()  # Reset state estimator to clear any erroneous state from before the stop
        await self.socketio.emit('resume', {"status": "success"})
            

    async def obstacle_stop(self):
        """Stop the robot for a short duration when an obstacle is detected."""
        await self.send_safe_command(Command.stop())  # Stop
    
    @staticmethod
    def bytes_to_sensor_data(data: bytes) -> SensorData:
        """Convert bytes to SensorData model."""

        # Look for start byte (0xAA)
        start_byte = data[0]
        if start_byte != 0xAA:
            logger = logging.getLogger("RobotManager")
            logger.error(f"Invalid start byte: {hex(start_byte)}, searching for 0xAA")
            raise ValueError("Invalid start byte")

        # Unpack the data according to the Arduino's sendSensorData format
        # <B    - start byte (0xAA)
        # B     - packet number (uint8_t) 
        # f     - distance_left (float)
        # f     - distance_right (float)
        # f     - distance_front (float)
        # h     - ax (int16_t)
        # h     - ay (int16_t)
        # h     - az (int16_t)
        # h     - gx (int16_t)
        # h     - gy (int16_t)
        # h     - gz (int16_t)
        # h     - tempC (float)
        # h     - magnetometer x (float, microtesla)
        # h     - magnetometer y (float, microtesla)
        # h     - magnetometer z (float, microtesla)
        # i     - left encoder ticks (int32_t)
        # i     - right encoder ticks (int32_t)
        # B     - flags (uint8_t) bit 0: new mag data, bit 1: motors enabled
        # B     - battery percentage (uint8_t)
        # I     - timestamp (uint32_t, microseconds)
        # B     - checksum (uint8_t)
        
        fields = struct.unpack('<BBfffhhhhhhhhhhiiBBIB', data)
        start, packet_num, distance_left, distance_right, distance_front, ax, ay, az, gx, gy, gz, temp, mag_x, mag_y, mag_z, left_encoder_ticks, right_encoder_ticks, flags, battery, timestamp, received_checksum = fields

        # Calculate checksum (sum of all bytes except checksum byte)
        calculated_checksum = sum(data[:-1]) & 0xFF
        valid = calculated_checksum == received_checksum

        if not valid:
            logger = logging.getLogger("RobotManager")
            logger.error(f"Invalid checksum: calculated={calculated_checksum}, received={received_checksum}")
           
        
        new_mag_data = bool(flags & 0b00000001)
        motors_enabled = bool(flags & 0b00000010)
        
        mag_heading = MagnetometerData.calculate_heading(mag_x, mag_y, mag_z)
        
        data = {
            "ultrasonic": {
                "distance_left": distance_left,
                "distance_right": distance_right
            },
            "tof": {
                "distance_front": distance_front
            },
            "imu": {
                "acceleration_x": ax * ROBOT_CONFIG.LSB_A , 
                "acceleration_y": ay * ROBOT_CONFIG.LSB_A,  
                "acceleration_z": az * ROBOT_CONFIG.LSB_A,  
                "gyroscope_x": gx * ROBOT_CONFIG.LSB_RAD,
                "gyroscope_y": gy * ROBOT_CONFIG.LSB_RAD,
                "gyroscope_z": gz * ROBOT_CONFIG.LSB_RAD,
                "temperature": temp * ROBOT_CONFIG.LSB_C + ROBOT_CONFIG.TEMP_OFFSET
            },
            "magnetometer": {
                "x": mag_x * ROBOT_CONFIG.LSB_uT,
                "y": mag_y * ROBOT_CONFIG.LSB_uT,
                "z": mag_z * ROBOT_CONFIG.LSB_uT,
                "heading": mag_heading,
                "new": new_mag_data
            },
            "left_encoder": left_encoder_ticks,
            "right_encoder": right_encoder_ticks,
            "battery": battery,
            "timestamp": timestamp,
            "packet_num": packet_num,
            "motors_enabled": motors_enabled
        }
        
        return SensorData.model_validate(data)
    
    def filter_distance(self, distance, left=True) -> float:
        distance_history = self.left_distance_history if left else self.right_distance_history
        if distance == -1:  # too far
            avg_distance = sum(distance_history) / len(distance_history) if distance_history else 300
            return avg_distance
        elif distance == -2:  # too close
            avg_distance = sum(distance_history) / len(distance_history) if distance_history else 0
        else:
            avg_distance = distance
            
        return avg_distance
        
    async def handle_obstacle(self, sensor_data: SensorData) -> tuple[float, float]:
        """Detect obstacles and trigger backup if needed. Returns processed distance."""
        distance_left = self.filter_distance(sensor_data.ultrasonic.distance_left)
        distance_right = self.filter_distance(sensor_data.ultrasonic.distance_right, left=False)

            
        async with self.state_lock:
            cur_state = self.state
            
        obstacle_detected = sensor_data.ultrasonic.obstacle_detected(ROBOT_CONFIG.OBSTACLE_DETECTED_THRESHOLD)
            
        if obstacle_detected == 0 or not self.obstacle_clear.is_set() or cur_state == Mode.STOPPED:
            return distance_left, distance_right
    
        await self.socketio.emit('obstacle_detected', {"distance_left": distance_left, "distance_right": distance_right})
    
        # If the distance is below the obstacle avoidance threshold, trigger backup and set obstacle clear flag
        
        '''
        obstacle_avoid = sensor_data.ultrasonic.obstacle_detected(ROBOT_CONFIG.OBSTACLE_AVOID_THRESHOLD)
        if obstacle_avoid > 0 and self.obstacle_clear.is_set():
            asyncio.create_task(self.obstacle_stop())
            self.obstacle_clear.clear()
            asyncio.create_task(self._reset_obstacle_clear())
        '''
        
        # Try lidar for obstacle avoidance
        if abs(self.repulsive_vector[1]) >= ROBOT_CONFIG.REPULSIVE_THRESHOLD:
            asyncio.create_task(self.obstacle_stop())
            self.obstacle_clear.clear()
            asyncio.create_task(self._reset_obstacle_clear())
            
        return distance_left, distance_right
        
    def process_sensor_data(self, data: bytes):
        try:
            new_data = self.bytes_to_sensor_data(data)
            
            self.last_sensor_receive_time = time.monotonic()
    
            with self.sensor_lock: # Ensure thread-safe access to latest_sensor_data
                self.previous_sensor_data = self.latest_sensor_data
                self.latest_sensor_data = new_data
                    
        except Exception as e:
            self._logger.error(f"Error processing sensor data: {e}")
            return
        
    async def process_lidar_data(self, data: any):
        lidar_data = LidarData.model_validate(data[0])
        
        async with self.lidar_lock:
            self.lidar_data = lidar_data
        
        print(lidar_data.get_repulsive_vector())
        
    async def send_sensor_update(self, current_time, sensor_data: SensorData):
        dt = 1 / ROBOT_CONFIG.EMIT_SENSOR_FREQ
        if current_time - self.last_emit_time >= dt:
            self.last_emit_time = current_time
            
                     
            async with self.state_lock:
                current_mode = self.state

            await self.socketio.emit(
                'sensor_data',
                {
                    "sensors": SensorData.clean(sensor_data.model_dump()), 
                    "state": SensorData.clean(self.state_estimator.state.model_dump()),
                    "mode": current_mode.name
                },
            )  
    
    async def debug_stall(self, start):
        no_data_for = start - self.last_sensor_receive_time
        freeze_log = f"No sensor data received for {no_data_for:.2f} seconds"

        since_last_cmd = start - self.last_command_sent_at if self.last_command_sent_at > 0 else None
        if since_last_cmd is not None and since_last_cmd <= self.freeze_after_cmd_window_s:
            freeze_log += (
                f" | freeze_after_cmd={self.last_command_type}"
                f" | cmd_id={self.last_command_id}"
                f" | cmd_age_ms={since_last_cmd * 1000:.0f}"
            )

        self._logger.warning(freeze_log)
        await self.emergency_stop()
        
    async def main_loop(self):
        """Main loop to continuously read sensor data and update state estimator."""
        dt = 1/ROBOT_CONFIG.MAIN_LOOP_FREQ
        self._logger.info("Running main loop: " + str(self.running))        
        while self.running:
            start = time.monotonic()
            
            if (start - self.last_sensor_receive_time) > ROBOT_CONFIG.SENSOR_TIMEOUT and self.state != Mode.STOPPED:
                await self.debug_stall(start)
                elapsed = time.monotonic() - start
                await asyncio.sleep(max(0.0001, dt - elapsed))
                continue
                    
            if self.sensor_lock.acquire(timeout=0.001):
                try:
                    sensor_data = self.latest_sensor_data
                    prev_data = self.previous_sensor_data
                finally:
                    self.sensor_lock.release()
            else:
                self._logger.warning("Sensor lock timeout")
                continue

            if not sensor_data:
                elapsed = asyncio.get_event_loop().time() - start
                # self._logger.warning("Skipping loop as no sensor data was recieve")
                await asyncio.sleep(max(0.0001, dt - elapsed)) # 100Hz loop
                continue

            async with self.state_lock:
                # Only check this if we have not recently recieved a resume command (since it might take a moment for the ESTOP command to be processed and for the state estimator to reset, we want to avoid immediately switching back to STOPPED mode if we receive sensor data with motors disabled right after a resume command)
                if self.state != Mode.STOPPED and sensor_data.motors_enabled == False and prev_data and prev_data.motors_enabled == True:
                    self._logger.warning("Motors manually disabled via ESTOP button, switching to STOPPED mode")
                    self.state = Mode.STOPPED
                cur_state = self.state
                
            async with self.lidar_lock:
                lidar_data = self.lidar_data
                self.repulsive_vector = lidar_data.get_repulsive_vector() if lidar_data is not None else (0, 0)
                self.lidar_data = None # Clear lidar data after reading it in the main loop, since it's only needed for obstacle detection and path following in the main loop, and we want to avoid processing stale lidar data in the next loop iteration
            
            if cur_state != Mode.STOPPED: # Only update state estimator if not stopped
                self.state_estimator.update(sensor_data, prev_data, lidar_data)

            if cur_state == Mode.PATH_FOLLOWING:
                if self.cur_path is None:
                    async with self.state_lock:
                        self.state = Mode.MANUAL
                else:
                    exit_path = False
                    if isinstance(self.cur_path, Path): # Quintic Hermite spline path using RAMSETE
                        ready = self.cur_path.is_ready()
                        
                        if ready:
                            if self.cur_path.complete():
                                exit_path = True
                            else:
                                sensor_dt = StateEstimator.calculate_dt(sensor_data.timestamp, prev_data.timestamp)
                                await self.send_safe_command(self.cur_path.get_command(self.state_estimator.state, sensor_dt))
                                
                    elif isinstance(self.cur_path, PurePursuit):
                        # Run pure pursuit
                        command = self.cur_path.calculate_control_command(self.state_estimator.state, self.repulsive_vector)
                        
                        if not command:
                            exit_path = True
                        else:
                            await self.send_safe_command(command)
                            
                    elif isinstance(self.cur_path, GoToGoal): # simple point goal (x, y)
                        command = self.cur_path.calculate_control_command(self.state_estimator.state, self.repulsive_vector)
                        if not command:
                            exit_path = True
                        else:
                            await self.send_safe_command(command)
                    else:
                        self._logger.error(f"Unknown path type: {type(self.cur_path)}")
                        exit_path = True
                        
                    if exit_path:
                        self._logger.info("Completed path")
                        async with self.state_lock:
                            self.state = Mode.MANUAL
                        self.cur_path = None
                        await self.send_safe_command(Command.stop())
                        await self.socketio.emit('path_complete', {"status": "success"})
            
            obstacle_dt = 1 / ROBOT_CONFIG.CHECK_OBSTACLE_FREQ
            
            # Only handle obstacle stopping and detection if in manual mode, since path following uses potential field control.
            if (start - self.last_obstacle_detect_time) >= obstacle_dt and self.state == Mode.MANUAL: 
                self.last_obstacle_detect_time = start
                # Will not backup if in STOPPED mode
                filtered_left, filtered_right = await self.handle_obstacle(sensor_data) ## Run simple smoothing via moving average and handle obstacle detection/backup
                self.latest_sensor_data.ultrasonic.distance_left = filtered_left
                self.latest_sensor_data.ultrasonic.distance_right = filtered_right
                self.left_distance_history.append(sensor_data.ultrasonic.distance_left) # Store the ultrasonic distance for history for smoothing
                self.right_distance_history.append(sensor_data.ultrasonic.distance_right)
            
            await self.send_sensor_update(start, sensor_data)
            elapsed = asyncio.get_event_loop().time() - start
           
            await asyncio.sleep(max(0.0001, dt - elapsed)) # 100Hz loop
        self._logger.info("Exited main loop")

    async def set_state(self, data):
        """Set the robot's state (manual, path following, stopped)"""
        resume = False
        async with self.state_lock:
            cur_state = self.state
            next_state = Mode[data["state"]]
            self._logger.info(f"Switching to state: {next_state}")            
            if next_state == Mode.PATH_FOLLOWING:
                if data["path_type"] == "spline":
                    try:
                        self.cur_path = Path.from_raw(data["path"]["splines"])
                        self.state = Mode.PATH_FOLLOWING
                    except ValueError:
                        self._logger.error("Invalid path data for spline path")
                        self.state = Mode.MANUAL
                elif data["path_type"] == "freehand":
                    self.cur_path = PurePursuit.from_xy_points(data["path"])
                    self.state = Mode.PATH_FOLLOWING
                elif data["path_type"] == "point":
                    self.cur_path = GoToGoal((data["path"]["x"], data["path"]["y"]))
                    self.state = Mode.PATH_FOLLOWING
                else:
                    self._logger.error(f"Unknown path type: {data['type']}")
                    self.state = Mode.MANUAL
                
            elif next_state == Mode.MANUAL:
                if cur_state == Mode.STOPPED:
                    resume = True
            elif next_state == Mode.STOPPED:
                await self.emergency_stop()
                
        if resume:
            await self.resume()
        
                
    async def handle_joystick_input(self, data):
        """
        Handle joystick input and send motor commands.
        """
        
        async with self.state_lock:
            cur_state = self.state
            
        if cur_state != Mode.MANUAL:
            return

        left_y = data.get('left_y', 0)
        right_x = data.get('right_x', 0)

        if self.obstacle_clear.is_set():
            if data.get("type"):
                await self.send_safe_command(Command.from_joystick(left_y, right_x, data["type"]))
            else:
                await self.send_safe_command(Command.from_joystick(left_y, right_x))
            

    async def _run_command_sequence(self, commands):
        """Run a sequence of commands."""
        try:
            for command in commands.commands:
                await self.socketio.emit('active_command', command.model_dump())
                await self.send_safe_command(command, wait_after=command.duration)
                    
                if command.pause_duration and command.command_type == CommandType.MOTOR:
                    await self.send_safe_command(Command.stop(), wait_after=command.pause_duration)
                    
            await self.send_safe_command(Command.stop())  # Ensure we stop the robot after the command sequence
            await self.socketio.emit('active_command', {
                "ID": ""
            })  # Clear active command
        except Exception as e:
            self._logger.error(f"Error running command sequence: {e}")
            await self.socketio.emit('active_command', {
                "ID": "",
                "error": str(e)
            })
            
    async def handle_query(self, query):
        
        # TODO: Overhaul LLM system to work with distances and velocities instead of duration
        await self.send_safe_command(
            Command(
                ID="",
                command_type=CommandType.LCD,
                command=LCDCommand(
                    line_1="Thinking...",
                    line_2=""
                ),
                pause_duration=0,
                duration=0
            )
        )
        
        commands = await text_to_command(query)
        command_task = asyncio.create_task(self._run_command_sequence(commands))
        return command_task
    

