from pydantic import Field, BaseModel
import math, numpy as np
from .VirtualObstacleType import VirtualObstacleType
from ..StateEstimation import RobotState

class VirtualObstacle(BaseModel):
    obstacle_type: VirtualObstacleType = Field(default=VirtualObstacleType.CIRCLE, description="Obstacle type (rectangle/circle)")
    position: tuple[float, float] = Field(default_factory=lambda: (0, 0,), description="XY position of the center of the obstacle in meters")
    rotation: float | None = Field(default=None, description="Rotation of the virtual obstacle in radians")
    width: float | None = Field(default=None, description="Width of the rectangular obstacle in meters")
    height: float | None = Field(default=None, description="Height of the rectangular obstacle in meters")
    radius: float | None = Field(default=None, description="Radius of the circular obstacle in meters")


    def get_bounding_box(self):
        return
        
    def rasterize(self, grid):
        return

    
    
