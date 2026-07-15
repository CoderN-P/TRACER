import logging
import queue
import time
from collections import deque
import asyncio
from .. import ROBOT_CONFIG, Mode
from .SensorData import SensorData
from .Lidar.LidarScan import LidarScan

class SensorDataManager:
    def __init__(self, state_manager, command_manager):
        self.sensor_queue = queue.Queue()
        self.lidar_queue = queue.Queue()
        self.last_sensor_receive_time = time.monotonic()
        self._logger = logging.getLogger("Robot.SensorDataManager")

        # Ultrasonic sensor smoothing
        self.left_distance_history: deque = deque(maxlen=50)  # Store last 10 distance readings for smoothing
        self.right_distance_history: deque = deque(maxlen=50)
        
        self.previous_sensor_data: SensorData | None = None
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
            distance_left = self.filter_distance(sensor_data.ultrasonic.distance_left)
            distance_right = self.filter_distance(sensor_data.ultrasonic.distance_right, left=False)
            sensor_data.ultrasonic.distance_left = distance_left
            sensor_data.ultrasonic.distance_right = distance_right
            self.add_sensor_data(sensor_data)
        except Exception as e:
            self._logger.error(f"Failed to parse sensor data: {e}")
            
            
    def add_sensor_data(self, sensor_data: SensorData):
        self.sensor_queue.put(sensor_data)
        self.last_sensor_receive_time = time.monotonic()
        
    def process_lidar_data(self, lidar_data: LidarScan):
        self.lidar_queue.put(lidar_data)

    async def debug_stall(self, start):
        no_data_for = start - self.last_sensor_receive_time
        freeze_log = f"No sensor data received for {no_data_for:.2f} seconds"

        since_last_cmd = start - self.command_manager.last_command_sent_at if self.command_manager.last_command_sent_at > 0 else None
        if since_last_cmd is not None and since_last_cmd <= self.command_manager.freeze_after_cmd_window_s:
            freeze_log += (
                f" | freeze_after_cmd={self.command_manager.last_command_type}"
                f" | cmd_id={self.command_manager.last_command_id}"
                f" | cmd_age_ms={since_last_cmd * 1000:.0f}"
            )

        self._logger.warning(freeze_log)
        await self.state_manager.emergency_stop()
        
    async def enforce_timeouts(self, start):
        dt = 1/ROBOT_CONFIG.MAIN_LOOP_FREQ
        if (start - self.last_sensor_receive_time) > ROBOT_CONFIG.SENSOR_TIMEOUT and await self.state_manager.get_state() != Mode.STOPPED:
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
        # Only check this if we have not recently recieved a resume command (since it might take a moment for the ESTOP command to be processed and for the state estimator to reset, we want to avoid immediately switching back to STOPPED mode if we receive sensor data with motors disabled right after a resume command)
        if state != Mode.STOPPED and sensor_data.motors_enabled == False and self.previous_sensor_data and self.previous_sensor_data.motors_enabled == True:
            self._logger.warning("Motors manually disabled via ESTOP button, switching to STOPPED mode")
            await self.state_manager.set_state({"state": "stopped"})
        if state == Mode.STOPPED and sensor_data.motors_enabled == True and self.previous_sensor_data and self.previous_sensor_data.motors_enabled == False:
            self._logger.warning("Motors manually re-enabled via ESTOP button, switching to MANUAL mode")
            await self.state_manager.set_state({"state": "manual"})            
