from pydantic import BaseModel, Field
import math
from . import ROBOT_CONFIG


class MagnetometerData(BaseModel):
    x: float = Field(..., description="Magnetic field strength in the X direction in microteslas (µT)")
    y: float = Field(..., description="Magnetic field strength in the Y direction in microteslas (µT)")
    z: float = Field(..., description="Magnetic field strength in the Z direction in microteslas (µT)")
    heading: float = Field(..., description="Heading calculated from magnetometer data in degrees")
    new: bool = Field(..., description="Indicates if the magnetometer data is new and has not been processed yet")
    
    @staticmethod
    def calculate_heading(x, y, z) -> float:
        cal_x, cal_y, cal_z = MagnetometerData.calibrate(x, y, z)
        heading_rad = math.atan2(cal_x, cal_y) # y axis is forward, x axis is right, z axis is down
        deg = math.degrees(heading_rad)
        
        # Normalize heading to [0, 360)
        if deg < 0:
            deg += 360
            
        return deg
    
    @staticmethod
    def calibrate(x, y, z):
        mx = x - ROBOT_CONFIG.MAGNETOMETER_HARD_IRON_OFFSETS[0]
        my = y - ROBOT_CONFIG.MAGNETOMETER_HARD_IRON_OFFSETS[1]
        mz = z - ROBOT_CONFIG.MAGNETOMETER_HARD_IRON_OFFSETS[2]
        
        cal_x = mx * ROBOT_CONFIG.MAGNETOMETER_SOFT_IRON_MATRIX[0][0] + my * ROBOT_CONFIG.MAGNETOMETER_SOFT_IRON_MATRIX[0][1] + mz * ROBOT_CONFIG.MAGNETOMETER_SOFT_IRON_MATRIX[0][2]
        cal_y = mx * ROBOT_CONFIG.MAGNETOMETER_SOFT_IRON_MATRIX[1][0] + my * ROBOT_CONFIG.MAGNETOMETER_SOFT_IRON_MATRIX[1][1] + mz * ROBOT_CONFIG.MAGNETOMETER_SOFT_IRON_MATRIX[1][2]
        cal_z = mx * ROBOT_CONFIG.MAGNETOMETER_SOFT_IRON_MATRIX[2][0] + my * ROBOT_CONFIG.MAGNETOMETER_SOFT_IRON_MATRIX[2][1] + mz * ROBOT_CONFIG.MAGNETOMETER_SOFT_IRON_MATRIX[2][2]
        
        return cal_x, cal_y, cal_z