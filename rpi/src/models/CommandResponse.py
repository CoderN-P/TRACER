from pydantic import BaseModel, Field
from .Command import Command

class AICommand(BaseModel):
    """
    Represents AI command response.
    """
    
    commands: list[Command] = Field(description="List of commands to be executed by the robot")