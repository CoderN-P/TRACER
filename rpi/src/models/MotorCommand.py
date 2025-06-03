from pydantic import BaseModel

class MotorCommand(BaseModel):
    """
    Represents a command to control both motors in differential drive.
    """
    left_motor: int # Speed for the left motor between -255 and 255
    right_motor: int  # Speed for the right motor between -255 and 255
