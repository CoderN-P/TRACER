from pydantic import BaseModel, Field
import math
from .. import ROBOT_CONFIG

class TwistCommand(BaseModel):
    v: float = Field(ge=-ROBOT_CONFIG.MAX_LINEAR_VEL_NEG, le=ROBOT_CONFIG.MAX_LINEAR_VEL_POS, description="Linear velocity in m/s")
    omega: float = Field(ge=-math.pi, le=math.pi, description="Angular velocity in rad/s")