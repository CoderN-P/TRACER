import logging
import queue
import time
import threading
from collections import deque
import asyncio
from .. import ROBOT_CONFIG, Mode
from .SensorData import SensorData
from .Lidar import LidarScan, PointCloud

class SensorDataManager:
    def __init__(self, state_manager, command_manager):
        self.sensor_queue = queue.Queue()
        self.lidar_queue = queue.Queue()
        self.receive_time_lock = threading.Lock()
        self.previous_data_lock = asyncio.Lock()
        self.last_sensor_receive_time = time.monotonic()
        self._logger = logging.getLogger("Robot.SensorDataManager")

        # Ultrasonic sensor smoothing
        self.left_distance_history: deque = deque(maxlen=50)  # Store last 10 distance readings for smoothing
        self.right_distance_history: deque = deque(maxlen=50)
        
        # Timing synchronization
        self.timing_offset_ns = None
        
        self.previous_sensor_data: SensorData | None = None
        self.previous_lidar_data: PointCloud | None = None
        self.state_manager = state_manager
        self.command_manager = command_manager

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
    
    def process_raw_sensor_data(self, raw_data: bytes):
        try:
            sensor_data = SensorData.from_bytes(raw_data)
            if self.timing_offset_ns is None:
                rpi_start_ns = time.perf_counter_ns()
                esp_start_us = sensor_data.timestamp
                self.timing_offset_ns = rpi_start_ns - esp_start_us*1000
                print(esp_start_us)
                self._logger.info(
                    f"ESP->RPi timing offset: {self.timing_offset_ns/1e9:.3f}s"
                )
            distance_left = self.filter_distance(sensor_data.ultrasonic.distance_left)
            distance_right = self.filter_distance(sensor_data.ultrasonic.distance_right, left=False)
            sensor_data.ultrasonic.distance_left = distance_left
            sensor_data.ultrasonic.distance_right = distance_right
            self.add_sensor_data(sensor_data)
        except Exception as e:
            self._logger.error(f"Failed to parse sensor data: {e}")
            
            
    def add_sensor_data(self, sensor_data: SensorData):
        # TODO: Handle microsecond rollover
        sensor_data.timestamp = sensor_data.timestamp*1000 + self.timing_offset_ns
        if abs(sensor_data.timestamp - time.perf_counter_ns()) > 1e9:
            self.timing_offset_ns += time.perf_counter_ns() - sensor_data.timestamp
        self.sensor_queue.put(sensor_data)
        with self.receive_time_lock:
            self.last_sensor_receive_time = time.monotonic()
    
    def process_lidar_data(self, lidar_data: LidarScan):
        self.lidar_queue.put(lidar_data)

    def get_last_sensor_receive_time(self):
        with self.receive_time_lock:
            return self.last_sensor_receive_time

    async def get_previous_sensor_data(self):
        async with self.previous_data_lock:
            return self.previous_sensor_data

    async def set_previous_sensor_data(self, sensor_data: SensorData | None):
        async with self.previous_data_lock:
            self.previous_sensor_data = sensor_data

    async def get_previous_lidar_data(self):
        async with self.previous_data_lock:
            return self.previous_lidar_data

    async def set_previous_lidar_data(self, lidar_data: PointCloud | None):
        async with self.previous_data_lock:
            self.previous_lidar_data = lidar_data

    async def get_previous_data_snapshot(self):
        async with self.previous_data_lock:
            return self.previous_sensor_data, self.previous_lidar_data

    async def debug_stall(self, start):
        no_data_for = start - self.get_last_sensor_receive_time()
        freeze_log = f"No sensor data received for {no_data_for:.2f} seconds"

        command_info = await self.command_manager.get_last_command_info()
        since_last_cmd = start - command_info["sent_at"] if command_info["sent_at"] > 0 else None
        if since_last_cmd is not None and since_last_cmd <= command_info["freeze_after_cmd_window_s"]:
            freeze_log += (
                f" | freeze_after_cmd={command_info['type']}"
                f" | cmd_id={command_info['id']}"
                f" | cmd_age_ms={since_last_cmd * 1000:.0f}"
            )

        self._logger.warning(freeze_log)
        await self.state_manager.emergency_stop()
        
    async def enforce_timeouts(self, start):
        dt = 1/ROBOT_CONFIG.EKF_FREQ
        if (start - self.get_last_sensor_receive_time()) > ROBOT_CONFIG.SENSOR_TIMEOUT and await self.state_manager.get_state() != Mode.STOPPED:
            await self.debug_stall(start)
            elapsed = asyncio.get_event_loop().time() - start
            await asyncio.sleep(max(0.0001, dt - elapsed))
            return False

        if self.sensor_queue.empty():
            elapsed = asyncio.get_event_loop().time() - start
            await asyncio.sleep(max(0.0001, dt - elapsed)) # 100Hz loop
            return False
        
        return True

    async def sync_with_embedded(self, sensor_data: SensorData):
        state = await self.state_manager.get_state()
        previous_sensor_data = await self.get_previous_sensor_data()
        # Only check this if we have not recently recieved a resume command (since it might take a moment for the ESTOP command to be processed and for the state estimator to reset, we want to avoid immediately switching back to STOPPED mode if we receive sensor data with motors disabled right after a resume command)
        if state != Mode.STOPPED and sensor_data.motors_enabled == False and previous_sensor_data and previous_sensor_data.motors_enabled == True:
            self._logger.warning("Motors manually disabled via ESTOP button, switching to STOPPED mode")
            await self.state_manager.set_state({"state": "STOPPED"})
        if state == Mode.STOPPED and sensor_data.motors_enabled == True and previous_sensor_data and previous_sensor_data.motors_enabled == False:
            self._logger.warning("Motors manually re-enabled via ESTOP button, switching to MANUAL mode")
            await self.state_manager.set_state({"state": "MANUAL"})            
