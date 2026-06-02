import math
from dataclasses import dataclass

@dataclass
class RobotConfig:
    WHEEL_BASE: float
    WHEEL_DIAMETER: float
    MAX_RPM: int
    REDUCTION_RATIO: float
    JOYSTICK_DEADZONE: float
    MAX_LATERAL_ACCEL: float
    MAX_LONG_ACCEL: float
    MAGNETOMETER_HARD_IRON_OFFSETS: tuple[float, float, float]
    MAGNETOMETER_SOFT_IRON_MATRIX: tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]
    CHECK_OBSTACLE_FREQ: float
    BACKUP_TIME: float
    OBSTACLE_DETECTED_THRESHOLD: float
    OBSTACLE_AVOID_THRESHOLD: float
    K_REPULSIVE_SOFT: int
    K_REPULSIVE_HARD: int
    REPULSIVE_THRESHOLD: float
    SYMMETRY_THRESHOLD: float
    K_NUDGE: float
    K_LIDAR_SHIFT: float
    K_US_SHIFT: float
    OBSTACLE_ALPHA: float
    MAX_SHIFT: float
    EMIT_SENSOR_FREQ: float
    SENSOR_TIMEOUT: float
    MAIN_LOOP_FREQ: float
    PATH_FOLLOWING_FREQ: float
    MANUAL_FREQ: float
    ENCODER_PPR: int
    MAX_ENCODER_MARGIN: float
    LEFT_CORRECTION_POS: float
    RIGHT_CORRECTION_POS: float
    LEFT_CORRECTION_NEG: float
    RIGHT_CORRECTION_NEG: float
    G: float
    LSB_G: float
    LSB_uT: float
    LSB_C: float
    TEMP_OFFSET: float
    P_THETA: float
    P_GYRO_BIAS: float
    P_THETA_BIAS: float
    P_POSITION: float
    Q_THETA: float
    Q_BIAS: float
    Q_X: float
    Q_Y: float
    R_THETA_ENCODER: float
    R_THETA_MAGNETOMETER: float
    R_POSITION: float
    STATE_HISTORY_SIZE: int
    LOOKAHEAD_DISTANCE: float
    COMPLETION_THRESHOLD: float
    MAX_SEARCH_POINTS: int
    END_LOOKAHEAD_MULTIPLIER: float
    K_CURVE: float
    BETA: float
    ZETA: float
    SPLINE_SAMPLES: int
    TRAJECTORY_DT: float
    K_OMEGA: float
    K_V: float
    K_D: float

    @property
    def WHEEL_RADIUS(self) -> float:
        return self.WHEEL_DIAMETER / 2.0

    @property
    def WHEEL_CIRCUMFERENCE(self) -> float:
        return math.pi * self.WHEEL_DIAMETER

    @property
    def MAX_LINEAR_VEL(self) -> float:
        return 0.43 # (self.MAX_RPM * self.WHEEL_CIRCUMFERENCE) / 60.0

    @property
    def ENCODER_TICKS_PER_REV(self) -> int:
        return int(self.ENCODER_PPR * self.REDUCTION_RATIO * 4)

    @property
    def METERS_PER_TICK(self) -> float:
        return self.WHEEL_CIRCUMFERENCE / self.ENCODER_TICKS_PER_REV

    @property
    def METERS_PER_TICK_LEFT_POS(self) -> float:
        return self.METERS_PER_TICK * self.LEFT_CORRECTION_POS

    @property
    def METERS_PER_TICK_RIGHT_POS(self) -> float:
        return self.METERS_PER_TICK * self.RIGHT_CORRECTION_POS

    @property
    def METERS_PER_TICK_LEFT_NEG(self) -> float:
        return self.METERS_PER_TICK * self.LEFT_CORRECTION_NEG

    @property
    def METERS_PER_TICK_RIGHT_NEG(self) -> float:
        return self.METERS_PER_TICK * self.RIGHT_CORRECTION_NEG

    @property
    def LSB_RAD(self) -> float:
        return 8.75 / 1000.0 * math.pi / 180.0

    @property
    def LSB_A(self) -> float:
        return self.LSB_G * self.G
