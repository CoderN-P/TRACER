from pydantic import BaseModel, Field

class Gap(BaseModel):
    start: int = Field(..., description="Starting index of the gap")
    end: int = Field(..., description="Ending index of the gap")
    center: float = Field(..., description="Center of the gap")
    
