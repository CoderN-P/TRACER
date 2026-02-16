from pydantic import BaseModel, Field

# Data class to store state estimates for the robot include pose, velocity, and other relevant information


class RobotState(BaseModel):
    """
    Represents the state of the robot, including pose, velocity, and other relevant information.
    """
    
    # Position
    x: float = Field(..., description="X position of the robot in centimeters")
    y: float = Field(..., description="Y position of the robot in centimeters")
    
    # Orientation
    yaw: float = Field(..., description="Heading of the robot in degrees")
    pitch: float = Field(..., description="Pitch of the robot in degrees")
    roll: float = Field(..., description="Roll of the robot in degrees")
    
    
    linear_velocity_x: float = Field(..., description="Linear velocity of the robot in cm/s in the X direction")
    linear_velocity_y: float = Field(..., description="Linear velocity of the robot in cm/s in the Y direction")
    angular_velocity: float = Field(..., description="Angular velocity of the robot in degrees/s")