import math
from dataclasses import dataclass

@dataclass(frozen=True) # frozen=True makes it read-only for safety
class RobotConfig:
    # Physical Dimensions (Meters)
    MEASURED_WHEEL_BASE: float = 0.21
    WHEEL_DIAMETER: float = 0.05411268
    WHEEL_RADIUS: float = WHEEL_DIAMETER / 2.0
    WHEEL_CIRCUMFERENCE: float = math.pi * WHEEL_DIAMETER

    WHEEL_BASE_CORRECTION: float = 1.0 # Ratio between true distance and encoder distance, to be calibrated
    WHEEL_BASE: float = MEASURED_WHEEL_BASE * WHEEL_BASE_CORRECTION
    # Motor Limits
    MAX_RPM: int = 178 / 2 # With 2S LiPo the motors receive less voltage and thus have a lower max RPM, so we cut it in half to be safe. This can be adjusted after testing.
    # Max speed in m/s: (RPM * pi * D) / 60
    MAX_LINEAR_VEL: float = (MAX_RPM * math.pi * WHEEL_DIAMETER) / 60.0
    
    REDUCTION_RATIO: float = 56.0 
    
    # Manual Control
    JOYSTICK_DEADZONE: float = 0.15 # Minimum joystick input to register movement
    
    # Environment
    MAX_LATERAL_ACCEL: float = 0.5 # m/s^2, for path following constraints
    
    # Magnetometer
    # TODO: Calibrate these values for the actual robot
    MAGNETOMETER_HARD_IRON_OFFSETS: tuple = (0.0, 0.0, 0.0) # microteslas (x, y, z)
    MAGNETOMETER_SOFT_IRON_MATRIX: tuple = (
        (1.0, 0.0, 0.0), # Row 1
        (0.0, 1.0, 0.0), # Row 2
        (0.0, 0.0, 1.0),  # Row 3
    )
    
    # Obstacle and Cliff avoidance
    CHECK_OBSTACLE_FREQ: float = 20.0 # Hz
    CHECK_CLIFF_FREQ: float = 20.0 # Hz
    BACKUP_TIME: float = 2.0 # s
    OBSTACLE_DETECTED_THRESHOLD: float = 20.0 # cm
    OBSTACLE_AVOID_THRESHOLD: float = 10.0 # cm
    
    # IO
    EMIT_SENSOR_FREQ: float = 10.0 # Hz
    
    # Loop
    MAIN_LOOP_FREQ: float = 100.0 # Hz
    
    # Encoders
    ENCODER_PPR: int = 11 # Pulses per revolution of the motor shaft
    ENCODER_TICKS_PER_REV: int = ENCODER_PPR * REDUCTION_RATIO * 4 # Pulses per revolution of the wheel 
    METERS_PER_TICK: float = WHEEL_CIRCUMFERENCE / ENCODER_TICKS_PER_REV
    
    LEFT_CORRECTION = 1 # Ratio between true distance and left encoder dist
    RIGHT_CORRECTION = 1 # Ratio between true distance and left encoder dist
    
    # TODO: Calibrate correction factors for each
    METERS_PER_TICK_LEFT: float = METERS_PER_TICK * LEFT_CORRECTION
    METERS_PER_TICK_RIGHT: float = METERS_PER_TICK * RIGHT_CORRECTION

    
    
    # State Estimation
    P_THETA: float = 0.1 # Uncertainty in heading (radians)
    P_GYRO_BIAS: float = 1.0e-4 # Uncertainty in gyro bias (rad/s)
    P_THETA_BIAS: float = 0.0 # Initial covariance between heading and gyro bias
    
    Q_THETA_1: float = 1.0e-4 # Process noise in heading (radians^2/s)
    Q_BIAS: float = 1.0e-6 # Process noise in gyro
    
    
    # not currently used, but could be added to the Kalman filter for better position estimation
    Q_X: float = 0.01 # Process noise in x position (meters^2/s)
    Q_Y: float = 0.01 # Process noise in y position (meters^2/s)
    Q_THETA_2: float = 5.0e-5 # Process noise in layer 2 heading
    
    R_THETA_ENCODER: float = 0.01 # Measurement noise from encoders (radians^2)
    R_THETA_MAGNETOMETER: float = 0.1
    
    # Pure Pursuit
    LOOKAHEAD_DISTANCE: float = 0.3 # Meters
    COMPLETION_THRESHOLD: float = 0.1 # Meters
    MAX_SEARCH_POINTS: int = 50 # Only search 50 points ahead in pure pursuit. 
    END_LOOKAHEAD_MULTIPLIER: float = 1.5 # Increase lookahead distance near the end of the path
    
    # RAMSETE
    RAMSETE_B: float = 2.0
    RAMSETE_ZETA: float = 0.7
    
    # Splines
    SPLINE_SAMPLES = 1000
    TRAJECTORY_DT = 0.01 # Time step for trajectory generation (seconds)
    