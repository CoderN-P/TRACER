from pydantic import BaseModel, Field


class UltrasonicSensor(BaseModel):
    """
    Represents the data from an ultrasonic sensor.
    """
    distance: float = Field(..., description="Distance measured by the ultrasonic sensor in centimeters")
    timestamp: str = Field(..., description="Timestamp of when the measurement was taken")
    
    def is_obstacle_detected(self, threshold: float = 10.0) -> bool:
        """
        Check if an obstacle is detected within a certain distance threshold.
        
        :param threshold: Distance in centimeters below which an obstacle is considered detected
        :return: True if an obstacle is detected, False otherwise
        """
        return self.distance < threshold