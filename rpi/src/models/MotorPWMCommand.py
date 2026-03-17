from pydantic import BaseModel, Field
from . import ROBOT_CONFIG

class MotorPWMCommand(BaseModel):
    """
    Represents a command to control both motors in differential drive.
    """
    left_motor: float = Field(ge=-1, le=1, description="PWM value for the left motor, range -1 to 1")
    right_motor: float = Field(ge=-1, le=1, description="PWM value for the right motor, range -1 to 1") 
