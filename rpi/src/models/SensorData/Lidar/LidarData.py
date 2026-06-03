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

    def get_repulsive_vector(self, sensor_data: SensorData):
        values = np.array(self.grid.values)  # shape (rows, cols, 2)
    
        lateral = values[:, :, 0]
        depth = values[:, :, 1]
        dist = np.linalg.norm(values, axis=2)
    
        # Mask valid points
        mask = (dist > 0) & (dist <= ROBOT_CONFIG.OBSTACLE_DETECTED_THRESHOLD/100.0) & (depth > 0)
    
        dist = np.where(mask, dist, 1.0)  # avoid division by zero
        depth_m = np.where(mask, depth, 0.0)
    
        # Compute magnitude
        hard_thresh = ROBOT_CONFIG.OBSTACLE_AVOID_THRESHOLD/100.0
        soft_thresh = ROBOT_CONFIG.OBSTACLE_DETECTED_THRESHOLD/100.0
    
        hard_mask = mask & (depth_m < hard_thresh)
        soft_mask = mask & (depth_m >= hard_thresh)
    
        magnitude = np.zeros_like(dist)
        magnitude = np.where(hard_mask, ROBOT_CONFIG.K_REPULSIVE_HARD * (1.0/depth_m - 1.0/hard_thresh), magnitude)
        magnitude = np.where(soft_mask, ROBOT_CONFIG.K_REPULSIVE_SOFT * (1.0/depth_m - 1.0/soft_thresh), magnitude)
        magnitude *= np.where(mask, depth_m/dist, 0.0)
    
        repulsive_x = -np.sum((lateral/dist) * magnitude * mask)
        repulsive_y = -np.sum((depth_m/dist) * magnitude * mask)
    
        count = np.sum(mask)
    
        if count > 0:
            repulsive_x /= count
            repulsive_y /= count
    
            if abs(repulsive_x) < ROBOT_CONFIG.SYMMETRY_THRESHOLD and abs(repulsive_y) > ROBOT_CONFIG.REPULSIVE_THRESHOLD:
                repulsive_x += ROBOT_CONFIG.K_NUDGE * abs(repulsive_y) * (sensor_data.ultrasonic.distance_right - sensor_data.ultrasonic.distance_left)
    
        return repulsive_x, repulsive_y
                