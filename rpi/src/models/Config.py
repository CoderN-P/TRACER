import math
from dataclasses import dataclass

@dataclass
class RobotConfig:
    # Physical Dimensions (Meters)
    MEASURED_WHEEL_BASE: float = 0.255
    WHEEL_DIAMETER: float = 0.05411268
    WHEEL_RADIUS: float = WHEEL_DIAMETER / 2.0
    WHEEL_CIRCUMFERENCE: float = 0.17

    WHEEL_BASE_CORRECTION: float = 1.0 # Ratio between true distance and encoder distance, to be calibrated
    # Motor Limits
    MAX_RPM: int = 178 
    # Max speed in m/s: (RPM * pi * D) / 60
    MAX_LINEAR_VEL: float = 0.4 # (MAX_RPM * WHEEL_CIRCUMFERENCE) / 60.0
    
    REDUCTION_RATIO: float = 56.0 
    
    # Manual Control
    JOYSTICK_DEADZONE: float = 0.15 # Minimum joystick input to register movement
    
    # Environment
    MAX_LATERAL_ACCEL: float = 0.3 # m/s^2, for path following constraints
    MAX_LONG_ACCEL: float = 0.8
    # Magnetometer
    # TODO: Calibrate these values for the actual robot
    MAGNETOMETER_HARD_IRON_OFFSETS: tuple = (0.0, 0.0, 0.0) # microteslas (x, y, z)
    MAGNETOMETER_SOFT_IRON_MATRIX: tuple = (
        (1.0, 0.0, 0.0), # Row 1
        (0.0, 1.0, 0.0), # Row 2
        (0.0, 0.0, 1.0),  # Row 3
    )
    
    # Obstacle avoidance
    CHECK_OBSTACLE_FREQ: float = 20.0 # Hz
    BACKUP_TIME: float = 2.0 # s
    OBSTACLE_DETECTED_THRESHOLD: float = 30.0 # cm
    OBSTACLE_AVOID_THRESHOLD: float = 20.0 # cm
    K_REPULSIVE_SOFT: int = 40
    K_REPULSIVE_HARD: int = 100
    K_ATTRACTIVE: int = 15
    REPULSIVE_THRESHOLD = 100 # Magnitude of repulsive vector before we begin backing up
    REPULSIVE_WEIGHT = 0.5 # Weight given to repulsive vector in path following
    
    # IO
    EMIT_SENSOR_FREQ: float = 10.0 # Hz
    SENSOR_TIMEOUT: float = 0.05  # Seconds without new sensor data before considering it a timeout
    
    # Loop
    MAIN_LOOP_FREQ: float = 100.0 # Hz
    
    # Encoders
    ENCODER_PPR: int = 11 # Pulses per revolution of the motor shaft
    ENCODER_TICKS_PER_REV: int = ENCODER_PPR * REDUCTION_RATIO * 4 # Pulses per revolution of the wheel 
    METERS_PER_TICK: float = WHEEL_CIRCUMFERENCE / ENCODER_TICKS_PER_REV
    MAX_ENCODER_MARGIN = 1.15  # 15% margin for acceleration transients when validating encoder readings
    
    # NOTE: Values calibrated for 3S LiPo (subject to change after testing)
    LEFT_CORRECTION = 0.951 # Ratio between true distance and left encoder dist
    RIGHT_CORRECTION = 1 # Ratio between true distance and right encoder dist
    
    METERS_PER_TICK_LEFT: float = METERS_PER_TICK * LEFT_CORRECTION
    METERS_PER_TICK_RIGHT: float = METERS_PER_TICK * RIGHT_CORRECTION
    
    # Sensor Constants
    G = 9.81 # m/s^2
    LSB_G = 0.061 / 1000.0 # +2g for accelerometer
    LSB_RAD = 8.75 / 1000.0 * math.pi / 180 # +250 dps (8.75 mdps per LSB converted to rad/s per LSB_
    LSB_A = LSB_G * G # Acceleration in m/s^2 per LSB
    LSB_uT = 1.0 / 120.0  # ±2G (gauss) full-scale for magnetometer
    LSB_C = 1.0 / 256.0 # Temperature in °C per LSB (from datasheet)
    TEMP_OFFSET = 25.0 # Temperature offset in °C (from datasheet, 0 LSB = 25°C)

    # State Estimation
    P_THETA: float = 0.1 # Initial Uncertainty in heading (radians)
    P_GYRO_BIAS: float = 1.0e-4 # Initial Uncertainty in gyro bias (rad/s)
    P_THETA_BIAS: float = 0.0 # Initial covariance between heading and gyro bias
    P_POSITION: float = 0.01 # Initial Uncertainty in position (meters)
    
    Q_THETA: float = 1.0e-4 # Process noise in heading (radians^2/s)
    Q_BIAS: float = 1.0e-6 # Process noise in gyro
    
    Q_X: float = 0.01 # Process noise in x position (meters^2/s)
    Q_Y: float = 0.01 # Process noise in y position (meters^2/s)
    
    R_THETA_ENCODER: float = 0.01 # Measurement noise from encoders (radians^2)
    R_THETA_MAGNETOMETER: float = 0.1 # Measurement noise from magnetometer (radians^2)
    R_POSITION: float = 0.05 # Measurement noise from LIDAR VIO positioning (meters^2)
    
    # Pure Pursuit
    LOOKAHEAD_DISTANCE: float = 0.4 # Meters
    COMPLETION_THRESHOLD: float = 0.04 # Meters
    MAX_SEARCH_POINTS: int = 50 # Only search 50 points ahead in pure pursuit. 
    END_LOOKAHEAD_MULTIPLIER: float = 1.1 # Increase lookahead distance near the end of the path
    
    # RAMSETE
    BETA: float = 3.2
    ZETA: float = 0.7
    
    # Splines
    SPLINE_SAMPLES = 1000
    TRAJECTORY_DT = 0.01 # Time step for trajectory generation (seconds)

    # Go to Goal
    K_OMEGA = 0.8
    K_V = 5.0
    K_D = 4.0
    
    @property
    def WHEEL_BASE(self) -> float:
        return self.MEASURED_WHEEL_BASE * self.WHEEL_BASE_CORRECTION