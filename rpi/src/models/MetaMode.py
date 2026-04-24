from enum import Enum

class MetaMode(str, Enum):
    """
    Represents the different meta modes for the robot, which define the overall behavior and control strategy of the robot.
    """
    USER = "user" # User mode where the robot is controlled by a human operator through manual commands
    LLM = "llm" # LLM mode where the robot is controlled by a large language model (LLM) that generates commands based on high-level instructions
    