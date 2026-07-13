from pydantic import BaseModel, Field
import datetime

class PathCompleted(BaseModel):
    timestamp: float = Field(default_factory=datetime.datetime.now, description="Timestamp when the path was completed")
    