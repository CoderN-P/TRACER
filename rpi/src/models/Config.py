import math
from dataclasses import dataclass

@dataclass(frozen=True) # frozen=True makes it read-only for safety
class RobotConfig:
    # Physical Dimensions (Meters)
    WHEEL_BASE: float = 0.21
    WHEEL_DIAMETER: float = 0.05
    WHEEL_RADIUS: float = WHEEL_DIAMETER / 2.0
    WHEEL_CIRCUMFERENCE: float = math.pi * WHEEL_DIAMETER

    # Motor Limits
    MAX_RPM: int = 178
    # Max speed in m/s: (RPM * pi * D) / 60
    MAX_LINEAR_VEL: float = (MAX_RPM * math.pi * WHEEL_DIAMETER) / 60.0
    REDUCTION_RATIO: float = 56.0 
    
    # Encoders
    ENCODER_PPR: int = 11 # Pulses per revolution of the motor shaft
    ENCODER_TICKS_PER_REV: int = ENCODER_PPR * REDUCTION_RATIO * 4 # Pulses per revolution of the wheel 
    METERS_PER_TICK: float = WHEEL_CIRCUMFERENCE / ENCODER_TICKS_PER_REV
    
    # State Estimation
    
    P_THETA: float = 0.1 # Uncertainty in heading (radians)
    P_GYRO_BIAS: float = 1.0e-4 # Uncertainty in gyro bias (rad/s)
    P_THETA_BIAS: float = 0.0 # Initial covariance between heading and gyro bias
    
    Q_THETA: float = 1.0e-4 # Process noise in heading (radians^2/s)
    Q_BIAS: float = 1.0e-6 # Process noise in gyro
    
    R_THETA_ENCODER: float = 0.01 # Measurement noise from encoders (radians^2)
    R_THETA_MAGNETOMETER: float = 0.1
    
    # Pure Pursuit
    LOOKAHEAD_DISTANCE: float = 0.3 # Meters
    COMPLETION_THRESHOLD: float = 0.1 # Meters
    END_LOOKAHEAD_MULTIPLIER: float = 1.5 # Increase lookahead distance near the end of the path