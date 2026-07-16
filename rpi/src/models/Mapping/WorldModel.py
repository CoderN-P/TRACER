import os
import datetime
from ..SensorData.Lidar import PointCloud
from . import LocalizationMode, StaticMapGrid, VirtualLayer, MAP_SAVE_DIR, LidarLayer


class WorldModel:
    def __init__(self, state_manager):
        self.static_map = StaticMapGrid()
        self.lidar_layer = LidarLayer()
        self.virtual_layer = VirtualLayer()
        
        self.state_manager = state_manager
        
    def update(self, point_cloud: PointCloud):
        self.lidar_layer.update(point_cloud)
        
        if self.state_manager.localization_state == LocalizationMode.MAP:
            self.static_map.update(point_cloud)
            
    def save(self, name):
        os.mkdir(MAP_SAVE_DIR / name)
        self.static_map.save_map(name)
        self.virtual_layer.save(name)
        
    def cost_at(self, x, y):
        static = self.static_map.cost_at(x,y)
        lidar = self.lidar_layer.cost_at(x,y)
        virtual = self.virtual_layer.cost_at(x,y)

        return max(static, lidar, virtual)
    
    def decay_live_layer(self):
        self.lidar_layer.decay()
        
    def serialize_visualization(self):
        return {
            "static": self.static_map.serialize_visualization(),
            "lidar": self.lidar_layer.serialize_visualization(),
        }

    def shutdown(self):
        # Saves the map with title timestamp if in mapping mode
        if self.state_manager.localization_state == LocalizationMode.MAP:
            self.save(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
