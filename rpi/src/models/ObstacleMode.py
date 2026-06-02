from enum import Enum

class ObstacleMode(str, Enum):
    """
    Represents the different obstacle avoidance modes for the robot, which define how the robot perceives and reacts to obstacles in its environment.
    """
    NORMAL = "normal" # Normal mode where the robot uses its ultrasonic, tof, and lidar sensors for obstacle avoidance
    VIRTUAL = "virtual" # Virtual mode where the robot avoids virtual obstacles and uses that information to simulate sensor data.
    