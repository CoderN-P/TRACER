from pydantic import Field, BaseModel
from typing import List
from .Point import Point

class PointCloud(BaseModel):
    timestamp: int = Field(..., description="Timestamp attributed to the point cloud")
    points: List[Point] = Field(..., description="Array of points in the point cloud")