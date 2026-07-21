import os
import datetime
import asyncio
from ..SensorData.Lidar import PointCloud
from . import LocalizationMode, StaticMapGrid, VirtualLayer, MAP_SAVE_DIR, LidarLayer


class WorldModel:
    def __init__(self, state_manager):
        self.static_map = StaticMapGrid()
        self.lidar_layer = LidarLayer()
        self.virtual_layer = VirtualLayer()
        self.map_lock = asyncio.Lock()
        
        self.state_manager = state_manager
        
    async def update(self, point_cloud: PointCloud):
        localization_state = await self.state_manager.get_localization_state()
        async with self.map_lock:
            self.lidar_layer.update(point_cloud)
            
            if localization_state == LocalizationMode.MAP:
                self.static_map.update(point_cloud)
            
    async def save(self, name):
        async with self.map_lock:
            os.mkdir(MAP_SAVE_DIR / name)
            self.static_map.save_map(name)
            self.virtual_layer.save(name)
        
    async def cost_at(self, x, y):
        async with self.map_lock:
            static = self.static_map.cost_at(x,y)
            lidar = self.lidar_layer.cost_at(x,y)
            virtual = self.virtual_layer.cost_at(x,y)

            return max(static, lidar, virtual)
    
    async def decay_live_layer(self):
        async with self.map_lock:
            self.lidar_layer.decay()
        
    async def serialize_visualization(self):
        async with self.map_lock:
            return {
                "static": self.static_map.serialize_visualization(),
                "lidar": self.lidar_layer.serialize_visualization(),
            }

    async def update_virtual_obstacles(self, obstacles):
        async with self.map_lock:
            self.virtual_layer.clear()
            self.virtual_layer.update(obstacles)

    async def get_static_map_snapshot(self):
        async with self.map_lock:
            return {
                "grid": self.static_map.grid.copy(),
                "scans_inserted": self.static_map.scans_inserted,
                "resolution": self.static_map.resolution,
                "origin_x": self.static_map.origin_x,
                "origin_y": self.static_map.origin_y,
            }

    async def shutdown(self):
        # Saves the map with title timestamp if in mapping mode
        localization_state = await self.state_manager.get_localization_state()
        if localization_state == LocalizationMode.MAP:
            await self.save(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
