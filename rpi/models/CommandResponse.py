from pydantic import BaseModel, Field
from typing import List
from . import Command

class AICommand(BaseModel):
    """
    Represents AI command response.
    """
    
    commands: List[Command] = Field(description="List of commands to be executed by the robot")