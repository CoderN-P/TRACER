import json
from . import MAP_SAVE_DIR
from .OccupancyGrid import OccupancyGrid
from ..SensorData import PointCloud
from ..StateEstimation import RobotState
from .. import ROBOT_CONFIG

class VirtualLayer(OccupancyGrid):
    def __init__(self):
        super().__init__(ROBOT_CONFIG.MAX_WORLD_WIDTH, ROBOT_CONFIG.MAX_WORLD_HEIGHT, ROBOT_CONFIG.GRID_RES)
        
    def update(self, virtual_obstacles: List[VirtualObstacle]):
        # Updates grid to occupy cells that are intersected by the virtual obstacles
        # Occupied = INF, free = 0
    
        raise NotImplementedError()
            
            
    
    def save(self, name): 
        save_dir = MAP_SAVE_DIR / name / "virtual_obstacles.json"
        
        json_data = {
            "obstacles": [
                self.virtual_obstacle.model_dump()
            ]
        }
        
        json.dump(save_dir, json_data)
        