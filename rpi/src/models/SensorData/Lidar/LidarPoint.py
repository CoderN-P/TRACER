from pydantic import BaseModel, Field
import math

class LidarPoint(BaseModel):
    angle: float = Field(ge=0.0, le=360.0, description="Angle of the lidar point measurement in degrees, where 0 degrees is facing forward and positive values are counterclockwise")
    distance: float = Field(ge=0, description="Distance of the lidar point measurement in meters")
    quality: float = Field(ge=0, le=63, description="Quality of the lidar point")
    timestamp_ns: int = Field(..., description="Timestamp of the lidar point measurement")
    
    def to_cartesian(self):
        """
        Convert the polar coordinates of the lidar point to Cartesian coordinates.
        Returns a tuple (x, y) in meters.
        """

        angle_rad = math.radians(self.angle)
        x = self.distance * math.cos(angle_rad)
        y = -self.distance * math.sin(angle_rad)
        return x, y, self.quality