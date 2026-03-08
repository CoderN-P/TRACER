from pydantic import BaseModel, Field
from . import ROBOT_CONFIG

class MotorCommand(BaseModel):
    """
    Represents a command to control both motors in differential drive.
    """
    left_motor: float = Field(ge=-ROBOT_CONFIG.MAX_LINEAR_VEL_LEFT, le=ROBOT_CONFIG.MAX_LINEAR_VEL_LEFT, description="Speed for the left motor, range -255 to 255")
    right_motor: float = Field(ge=-ROBOT_CONFIG.MAX_LINEAR_VEL_RIGHT, le=ROBOT_CONFIG.MAX_LINEAR_VEL_RIGHT, description="Speed for the right motor, range -255 to 255") 
 