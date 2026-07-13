from pydantic import BaseModel, Field
from .. import Mode

class StateChange(BaseModel):
    prev_state: Mode = Field(..., description="Previous state")
    new_state: Mode = Field(..., description="New state")
    data: dict | None = Field(default_factory=lambda: None, description="Additional data associated with the state change")