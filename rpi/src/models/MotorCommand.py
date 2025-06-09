from pydantic import BaseModel, Field

class MotorCommand(BaseModel):
    """
    Represents a command to control both motors in differential drive.
    """
    left_motor: int = Field(ge=-255, le=255, description="Speed for the left motor, range -255 to 255")
    right_motor: int = Field(ge=-255, le=255, description="Speed for the right motor, range -255 to 255") 
 