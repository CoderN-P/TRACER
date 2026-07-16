from pydantic import BaseModel, Field

class Point(BaseModel):
    x: float = Field(..., description="X coordinate of the point")
    y: float = Field(..., description="Y coordinate of the point")
    origin_x: float = Field(..., description="X coordinate of ray origin")
    origin_y: float = Field(..., description="Y coordinate of ray origin")
    quality: float = Field(ge=0, le=63, description="Quality of the point")
