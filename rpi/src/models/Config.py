from dataclasses import dataclass

@dataclass(frozen=True) # frozen=True makes it read-only for safety
class RobotConfig:
    # Physical Dimensions (Meters)
    WHEEL_BASE: float = 0.21
    WHEEL_DIAMETER: float = 0.05
    WHEEL_RADIUS: float = WHEEL_DIAMETER / 2.0

    # Motor Limits
    MAX_RPM: int = 178
    # Max speed in m/s: (RPM * pi * D) / 60
    MAX_LINEAR_VEL: float = (MAX_RPM * 3.14159 * WHEEL_DIAMETER) / 60.0

    # Pure Pursuit
    LOOKAHEAD_DISTANCE: float = 0.3 # Meters
    COMPLETION_THRESHOLD: float = 0.1 # Meters
    END_LOOKAHEAD_MULTIPLIER: float = 1.5 # Increase lookahead distance near the end of the path