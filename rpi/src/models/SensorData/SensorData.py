import numpy as np
from pydantic import BaseModel, Field
from . import UltrasonicSensor, IMUData, MagnetometerData, TOFData


class SensorData(BaseModel):
    """
    Represents sensor data from the robot.
    """
    ultrasonic: UltrasonicSensor = Field(..., description="Data from the ultrasonic sensor")
    imu: IMUData = Field(..., description="Data from the IMU (Inertial Measurement Unit)")
    tof: TOFData = Field(..., description="Data from the Time-of-Flight sensor")
    magnetometer: MagnetometerData = Field(..., description="Data from the magnetometer")
    left_encoder: int = Field(..., description="Left wheel encoder delta ticks")
    right_encoder: int = Field(..., description="Right wheel encoder delta ticks")
    battery: int = Field(..., description="Battery level in percentage (0-100)")
    timestamp: int = Field(..., description="Timestamp of the sensor data in microseconds since epoch") 
    packet_num: int = Field(..., description="Packet number for tracking sensor data updates")
    motors_enabled: bool = Field(..., description="Whether the motors are currently enabled")
    
    def is_obstacle_detected(self, threshold: float = 10.0) -> bool:
        """
        Check if an obstacle is detected based on the ultrasonic sensor data.
        
        :param threshold: Distance in centimeters below which an obstacle is considered detected
        :return: True if an obstacle is detected, False otherwise
        """
        return self.ultrasonic.is_obstacle_detected(threshold)
    
    def check_cliff(self) -> bool:
        """
        Check if a cliff is detected based on the IR sensors.
        
        :return: True if a cliff is detected, False otherwise
        """
        return not (self.ir_front and self.ir_back)

    @staticmethod
    def clean(x):

        if isinstance(x, dict):
            return {k: SensorData.clean(v) for k, v in x.items()}

        if isinstance(x, (np.floating,)):
             return float(x)

        if isinstance(x, (np.integer,)):
             return int(x)

        return x
