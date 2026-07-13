from pydantic import BaseModel, Field

class PathError(BaseModel):
    reason: str = Field(..., description="Reason for path error")
    