from pydantic import BaseModel, Field


class LidarGrid(BaseModel):
    """
    Represents a grid of LIDAR distance measurements.
    """
    cols: int = Field(..., description="Number of columns in the LIDAR grid")
    rows: int = Field(..., description="Number of rows in the LIDAR grid")
    width: float = Field(..., description="Physical width of the grid in meters")
    height: float = Field(..., description="Physical height of the grid in meters")
    values: list[list[list[float]]] = Field(..., description="2D list of xy distance measurements in centimeters, where values[row][col] corresponds to the [x, y] distance at that grid cell")