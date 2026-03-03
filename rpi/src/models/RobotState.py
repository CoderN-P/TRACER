from pydantic import BaseModel, Field

# Data class to store state estimates for the robot include pose, velocity, and other relevant information


class RobotState(BaseModel):
    """
    Represents the state of the robot, including pose, velocity, and other relevant information.
    """
    
    # Position
    x: float = Field(..., description="X position of the robot in meters")
    y: float = Field(..., description="Y position of the robot in meters")
    
    # Orientation
    yaw: float = Field(..., description="Heading of the robot in radians")
    pitch: float = Field(..., description="Pitch of the robot in radians") # Not used currently
    roll: float = Field(..., description="Roll of the robot in radians") # Not used currently
    
    
    linear_velocity: float = Field(..., description="Linear velocity of the robot in cm/s in its forward direction")
    angular_velocity: float = Field(..., description="Angular velocity of the robot in radians/s")