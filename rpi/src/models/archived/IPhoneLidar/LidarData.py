from pydantic import BaseModel, Field, model_validator
import numpy as np
from ..SensorData import SensorData
from .LidarCamera import LidarCamera
from .LidarGrid import LidarGrid
from ... import ROBOT_CONFIG


class LidarData(BaseModel):
    """
    Represents the data from iPhone LIDAR sensor.
    """
    timestamp: int = Field(..., description="Timestamp of the LIDAR reading in microseconds since epoch")
    camera: LidarCamera = Field(..., description="Position and orientation of the LIDAR camera")
    grid: LidarGrid = Field(..., description="Grid of distance measurements from the LIDAR sensor")


    @model_validator(mode='after')
    def swap_xy(self):
        self.camera.y, self.camera.x = -self.camera.x, self.camera.y
        return self
                
