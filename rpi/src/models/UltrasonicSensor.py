from pydantic import BaseModel, Field


class UltrasonicSensor(BaseModel):
    """
    Represents the data from an ultrasonic sensor.
    """
    distance_left: float = Field(..., description="Distance measured by the left ultrasonic sensor in centimeters")
    distance_right: float = Field(..., description="Distance measured by the right ultrasonic sensor in centimeters")
    
    
    def obstacle_detected(self, threshold: float = 10.0) -> int:
        """
        Check if an obstacle is detected based on the distance measurements.
        
        :param threshold: Distance in centimeters below which an obstacle is considered detected
        :return: 0 if no obstacle, 1 if obstacle on left, 2 if obstacle on right, 3 if obstacles on both sides
        """
        left_obstacle = self.distance_left < threshold
        right_obstacle = self.distance_right < threshold
        
        if left_obstacle and right_obstacle:
            return 3
        elif left_obstacle:
            return 1
        elif right_obstacle:
            return 2
        else:
            return 0