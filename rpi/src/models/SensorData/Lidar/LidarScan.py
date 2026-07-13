from pydantic import Field, BaseModel
from typing import List
from .LidarPoint import LidarPoint

class LidarScan(BaseModel):
    start_time_ns: int = Field(..., description="Start timestamp")
    end_time_ns: int = Field(..., description="End timestamp")
    points: List[LidarPoint] = Field(..., description="Array of lidar points collected in this scan")
    
    def to_cartesian(self):
        """
        Convert the polar coordinates of all lidar points in the scan to Cartesian coordinates.
        Returns a list of tuples [(x1, y1), (x2, y2), ...] in meters.
        """
        return [point.to_cartesian() for point in self.points]