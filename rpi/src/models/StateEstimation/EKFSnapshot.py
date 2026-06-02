from pydantic import BaseModel, Field
import numpy as np
from ..SensorData import SensorData
from .RobotState import RobotState

class EKFSnapshot(BaseModel):
    timestamp: int = Field(..., description="Microseconds since epoch of this snapshot")
    robot_state: RobotState = Field(..., description="Estimated robot state at snapshot")
    sensor_data: SensorData = Field(..., description="Sensor data control inputs at snapshot")
    heading_covariance: list = Field(..., description="Covariance matrix of heading")
    pose_covariance: list = Field(..., description="Covariance matrix of pose (x, y)")
    
    ## Hidden state var
    gyro_bias: float = Field(..., description="Heading filter hidden state variable")
    theta_encoders: float = Field(..., description="Accumulated heading from encoders")