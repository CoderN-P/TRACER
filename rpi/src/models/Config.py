import math
from dataclasses import dataclass

@dataclass
class RobotConfig:
    # Physical Dimensions (Meters)
    MEASURED_WHEEL_BASE: float = 0.255
    WHEEL_DIAMETER: float = 0.05411268

    WHEEL_BASE_CORRECTION: float = 1.0 # Ratio between true distance and encoder distance, to be calibrated
    # Motor Limits
    MAX_RPM: int = 178 
    # Max speed in m/s: (RPM * pi * D) / 60 - exposed as property
    
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
    REPULSIVE_THRESHOLD = 100 # Magnitude of repulsive vector before we begin backing up
    SYMMETRY_THRESHOLD = 0.5 # Max magnitude of lateral force before we stop applying nudge
    K_NUDGE = 0.5 # How much to nudge the lidar lateral force when we hit an obstacle head on
    K_LIDAR_SHIFT = 0.001 # Convert from repulsive force to lateral shift
    K_US_SHIFT = 0.5
    OBSTACLE_ALPHA = 0.9
    MAX_SHIFT = 0.003
    
    # IO
    EMIT_SENSOR_FREQ: float = 10.0 # Hz
    SENSOR_TIMEOUT: float = 0.05  # Seconds without new sensor data before considering it a timeout
    
    # Loop
    MAIN_LOOP_FREQ: float = 100.0 # Hz
    
    # Encoders
    ENCODER_PPR: int = 11 # Pulses per revolution of the motor shaft
    MAX_ENCODER_MARGIN = 1.15  # 15% margin for acceleration transients when validating encoder readings
    
    # NOTE: Values calibrated for 3S LiPo (subject to change after testing)
    LEFT_CORRECTION = 0.951 # Ratio between true distance and left encoder dist
    RIGHT_CORRECTION = 1 # Ratio between true distance and right encoder dist
    
    
    
    # Sensor Constants
    G = 9.81 # m/s^2
    LSB_G = 0.061 / 1000.0 # +2g for accelerometer
    
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
    LOOKAHEAD_DISTANCE: float = 0.2 # Meters
    COMPLETION_THRESHOLD: float = 0.01 # Meters
    MAX_SEARCH_POINTS: int = 50 # Only search 50 points ahead in pure pursuit. 
    END_LOOKAHEAD_MULTIPLIER: float = 1.1 # Increase lookahead distance near the end of the path
    K_CURVE = 0.1
    
    # RAMSETE
    BETA: float = 3.2
    ZETA: float = 0.7
    
    # Splines
    SPLINE_SAMPLES = 1000
    TRAJECTORY_DT = 0.01 # Time step for trajectory generation (seconds)

    # Go to Goal
    K_OMEGA = 3.14
    K_V = 6.0
    K_D = 7.0
    
    @property
    def WHEEL_BASE(self) -> float:
        return self.MEASURED_WHEEL_BASE * self.WHEEL_BASE_CORRECTION

    @property
    def WHEEL_RADIUS(self) -> float:
        return self.WHEEL_DIAMETER / 2.0

    @property
    def WHEEL_CIRCUMFERENCE(self) -> float:
        return math.pi * self.WHEEL_DIAMETER

    @property
    def MAX_LINEAR_VEL(self) -> float:
        return 0.4 # (self.MAX_RPM * self.WHEEL_CIRCUMFERENCE) / 60.0

    @property
    def ENCODER_TICKS_PER_REV(self) -> int:
        return int(self.ENCODER_PPR * self.REDUCTION_RATIO * 4)

    @property
    def METERS_PER_TICK(self) -> float:
        return self.WHEEL_CIRCUMFERENCE / self.ENCODER_TICKS_PER_REV

    @property
    def METERS_PER_TICK_LEFT(self) -> float:
        return self.METERS_PER_TICK * self.LEFT_CORRECTION

    @property
    def METERS_PER_TICK_RIGHT(self) -> float:
        return self.METERS_PER_TICK * self.RIGHT_CORRECTION

    @property
    def LSB_RAD(self) -> float:
        return 8.75 / 1000.0 * math.pi / 180.0

    @property
    def LSB_A(self) -> float:
        return self.LSB_G * self.G
