from pydantic import BaseModel, Field

class Gap(BaseModel):
    start: int = Field(..., description="Starting index of the gap")
    end: int = Field(..., description="Ending index of the gap")
    center: int = Field(..., description="Center index of the gap")
    