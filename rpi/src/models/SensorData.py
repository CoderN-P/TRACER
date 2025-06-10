from pydantic import BaseModel, Field
from . import UltrasonicSensor, IMUData


class SensorData(BaseModel):
    """
    Represents sensor data from the robot.
    """
    ultrasonic: UltrasonicSensor = Field(..., description="Data from the ultrasonic sensor")
    imu: IMUData = Field(..., description="Data from the IMU (Inertial Measurement Unit)")
    ir_front: bool = Field(..., description="Front IR sensor status (True if floor is detected)")
    ir_back: bool = Field(..., description="Back IR sensor status (True if floor is detected)")
    battery: int = Field(..., description="Battery level in percentage (0-100)")
    
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