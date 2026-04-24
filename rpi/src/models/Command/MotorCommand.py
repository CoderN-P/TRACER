from pydantic import BaseModel, Field
from .. import ROBOT_CONFIG

class MotorCommand(BaseModel):
    """
    Represents a command to control both motors in differential drive.
    """
    left_motor: float = Field(ge=-ROBOT_CONFIG.MAX_LINEAR_VEL, le=ROBOT_CONFIG.MAX_LINEAR_VEL, description="Speed for the left motor in m/s")
    right_motor: float = Field(ge=-ROBOT_CONFIG.MAX_LINEAR_VEL, le=ROBOT_CONFIG.MAX_LINEAR_VEL, description="Speed for the right motor in m/s") 
