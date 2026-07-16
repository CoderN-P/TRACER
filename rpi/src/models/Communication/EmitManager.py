import datetime
import asyncio
import time
from ..SensorData import SensorData
from .. import ROBOT_CONFIG

class EmitManager:
    def __init__(self, socket_manager, state_manager, manual_manager, loop_monitoring):
        self.socket_manager = socket_manager
        self.state_manager = state_manager
        self.loop_monitoring = loop_monitoring
        self.manual_manager = manual_manager

        self.sensor_update_dt = 1 / ROBOT_CONFIG.EMIT_SENSOR_FREQ
        self.map_update_dt = 1 / ROBOT_CONFIG.EMIT_MAP_FREQ
        self.last_emit_time: float = 0.0
        self.last_map_emit_time: float = 0.0

    async def send_sensor_update(self, sensor_data, robot_state, lidar_data):
        cur_time = asyncio.get_event_loop().time()
        if cur_time - self.last_emit_time < self.sensor_update_dt:
            return
            
        self.last_emit_time = cur_time

        current_mode = await self.state_manager.get_state()

        packet = {
            "sensors": SensorData.clean(sensor_data.model_dump()),
            "state": SensorData.clean(robot_state.model_dump()),
            "mode": current_mode.name,
            "localization_mode": self.state_manager.localization_state.name,
            "latest_lidar_scan": SensorData.clean(lidar_data.model_dump()) if lidar_data else None,
            "timestamp": datetime.datetime.now().isoformat(),
            "max_loop_time": self.loop_monitoring.max_loop_time,
            "velocity_profile_t": time.monotonic() - self.manual_manager.velocity_profile_manager.velocity_profile_start if self.manual_manager.velocity_profile_manager.velocity_profile_start else None,
        }
        
            
        await self.socket_manager.socketio.emit("sensor_data", packet)
        self.loop_monitoring.max_loop_time = 0.0
        
    async def send_map_update(self):
        cur_time = asyncio.get_event_loop().time()
        if cur_time - self.last_map_emit_time < self.map_update_dt:
            return
        
        self.last_map_emit_time = cur_time
        packet = self.socket_manager.world_model.serialize_visualization()
        await self.socket_manager.socketio.emit("map_update", packet)
