from enum import Enum

class Mode(str, Enum):
    """
    Represents the different control modes for the robot.
    """
    MANUAL = "manual" # Manual control mode where the user directly controls the robot from UI, joystick, or gesture control
    PATH_FOLLOWING = "path_following" # Autonomous mode where the robot follows a predefined path using pure pursuit
    STOPPED = "stopped" # Stopped mode where the robot is not executing any commands and is stationary