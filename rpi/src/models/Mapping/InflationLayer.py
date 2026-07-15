import logging
from .OccupancyGrid import OccupancyGrid
from ..SensorData import PointCloud
from ..StateEstimation import RobotState
from .. import ROBOT_CONFIG

class InflationLayer(OccupancyGrid):
    def __init__(self, lidar_layer, static_layer, virtual_layer):
        super().__init__(ROBOT_CONFIG.MAX_WORLD_WIDTH, ROBOT_CONFIG.MAX_WORLD_HEIGHT, ROBOT_CONFIG.GRID_RES)
        self._logger = logging.getLogger("Robot.WorldModel.InflationLayer")
        self.lidar_layer = lidar_layer
        self.static_layer = static_layer
        self.virtual_layer = virtual_layer
        
    def update(self):
        return
        
        