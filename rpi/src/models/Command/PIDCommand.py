from pydantic import BaseModel, Field


class PIDCommand(BaseModel):
    """
    Represents a command to control the LCD display.
    """
    p_left: float = Field(default=0.0, description="P term in left motor PID controller")
    p_right: float = Field(default=0.0, description="P term in right motor PID controller")
    i_left: float = Field(default=0.0, description="I term in left motor PID controller")
    i_right: float = Field(default=0.0, description="I term in right motor PID controller")
    d_left: float = Field(default=0.0, description="D term in left motor PID controller")
    d_right: float = Field(default=0.0, description="D term in right motor PID controller")
    
   