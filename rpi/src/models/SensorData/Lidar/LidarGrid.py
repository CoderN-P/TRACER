from pydantic import BaseModel, Field


class LidarGrid(BaseModel):
    """
    Represents a grid of LIDAR distance measurements.
    """
    values: list[list[float]] = Field(..., description="2D list of depth measurements in meters, where values[row][col] corresponds to the depth at that grid point")