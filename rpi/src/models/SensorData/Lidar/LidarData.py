from pydantic import BaseModel, Field
import numpy as np
from .LidarCamera import LidarCamera
from .LidarGrid import LidarGrid
from ... import ROBOT_CONFIG


class LidarData(BaseModel):
    """
    Represents the data from iPhone LIDAR sensor.
    """
    timestamp: float = Field(..., description="Timestamp of the LIDAR reading in seconds since epoch")
    camera: LidarCamera = Field(..., description="Position and orientation of the LIDAR camera")
    grid: LidarGrid = Field(..., description="Grid of distance measurements from the LIDAR sensor")
    
    
    
    def get_repulsive_vector(self):
        """
            Computes a repulsive vector based on the LIDAR grid data to help avoid obstacles.
            The vector is calculated by summing the contributions from each grid cell, where each contribution is inversely proportional to the distance measured in that cell and points away from the obstacle.
            :return: 
        """
        
        repulsive_x, repulsive_y = 0.0, 0.0
        count = 0
        
        for row in range(self.grid.rows):
            for col in range(self.grid.cols):
                vec = self.grid.values[row][col]
                dist = np.linalg.norm(vec)
                
                if not (0 < dist <= ROBOT_CONFIG.OBSTACLE_DETECTED_THRESHOLD/10.0):
                    continue
                    
                direction = np.array(vec) / dist
                
                if dist <= ROBOT_CONFIG.OBSTACLE_AVOID_THRESHOLD:
                    magnitude = ROBOT_CONFIG.K_REPULSIVE_HARD * (1.0 / dist - 1.0 / (ROBOT_CONFIG.OBSTACLE_DETECTED_THRESHOLD/10.0)) 
                else:
                    magnitude = ROBOT_CONFIG.K_REPULSIVE_SOFT * (1.0 / dist - 1.0 / (ROBOT_CONFIG.OBSTACLE_DETECTED_THRESHOLD/10.0))
                    
                repulsive_x -= direction[0] * magnitude
                repulsive_y -= direction[1] * magnitude
                
                count += 1  
                
                
        if count > 0:
            repulsive_x /= count
            repulsive_y /= count
            
        return repulsive_x, repulsive_y
                