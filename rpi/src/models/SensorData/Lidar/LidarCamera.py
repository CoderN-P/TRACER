from pydantic import BaseModel, Field, model_validator


class LidarCamera(BaseModel):
    """
    Represents the lidar camera position data 
    """
    x: float = Field(..., description="X coordinate of the lidar camera position in centimeters")
    y: float = Field(..., description="Y coordinate of the lidar camera position in centimeters")
    theta: float = Field(..., description="Orientation of the lidar camera in degrees, where 0 degrees is facing forward and positive values are counterclockwise")


    @model_validator(mode='after')
    def swap_xy(self):
        self.y, self.x = self.x, self.y
    
                     