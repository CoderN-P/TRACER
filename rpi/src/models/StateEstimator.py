import math
from .RobotState import RobotState
from .SensorData import SensorData
from .HeadingFilter import HeadingFilter
from . import ROBOT_CONFIG


class StateEstimator:
    def __init__(self):
        self.state = RobotState(
            x=0.0,
            y=0.0,
            yaw=0.0,
            pitch=0.0,
            roll=0.0,
            linear_velocity_x=0.0,
            linear_velocity_y=0.0,
            angular_velocity=0.0
        )
        
        # Pre state estimations
        self.initial_mag_heading = None
        self.theta_encoders = 0.0
        
        self.heading_filter = HeadingFilter()
    
    def initialize(self, sensor_data: SensorData):
        self.initial_mag_heading = math.radians(sensor_data.magnetometer_heading)
        
        
    def reset(self):
        self.state = RobotState(
            x=0.0,
            y=0.0,
            yaw=0.0,
            pitch=0.0,
            roll=0.0,
            linear_velocity_x=0.0,
            linear_velocity_y=0.0,
            angular_velocity=0.0
        )

    # Python logic to find how many packets were missed
    @staticmethod
    def calculate_missed_packets(current_seq, last_seq):
        # This handles the rollover (255 -> 0)
        diff = (current_seq - last_seq) & 0xFF
        return diff - 1 # If diff is 1, 0 packets were missed
    
    @staticmethod
    def calculate_dt(cur_raw: float, previous_raw: float):
        current_time = cur_raw / 1_000_000.0
        previous_time = previous_raw / 1_000_000.0
        
        if current_time < previous_time:
            dt = (current_time + (4294.9673 - previous_time))  # Handle rollover (4.2949673 seconds for 32-bit microsecond timer)
        else:
            dt = current_time - previous_time
            
        return dt

    @staticmethod
    def estimate_linear_velocity(left_ticks, right_ticks, dt):
        delta_left = left_ticks * (math.pi * ROBOT_CONFIG.WHEEL_DIAMETER) / ROBOT_CONFIG.ENCODER_TICKS_PER_REV
        delta_right = right_ticks * (math.pi * ROBOT_CONFIG.WHEEL_DIAMETER) / ROBOT_CONFIG.ENCODER_TICKS_PER_REV
        linear_velocity = (delta_left + delta_right) / (2 * dt)
        return linear_velocity
            
        
    def update(self, sensor_data: SensorData, previous_sensor_data: SensorData):
        # Previous sensor data is needed to determine dt
        dt = self.calculate_dt(sensor_data.timestamp, previous_sensor_data.timestamp)
        self.theta_encoders += self.heading_delta_from_encoders(sensor_data.left_encoder_ticks, sensor_data.right_encoder_ticks)
        yaw_filtered = self.heading_filter.step(self.theta_encoders, sensor_data.gyro_z, dt)
        linear_vel = self.estimate_linear_velocity(sensor_data.left_encoder_ticks, sensor_data.right_encoder_ticks, dt)
        
        
        
        return
    
    def heading_delta_from_encoders(self, left_ticks, right_ticks):
        delta_left = left_ticks * (math.pi * ROBOT_CONFIG.WHEEL_DIAMETER) / ROBOT_CONFIG.ENCODER_TICKS_PER_REV
        delta_right = right_ticks * (math.pi * ROBOT_CONFIG.WHEEL_DIAMETER) / ROBOT_CONFIG.ENCODER_TICKS_PER_REV
        delta_theta = (delta_right - delta_left) / ROBOT_CONFIG.WHEEL_BASE_WIDTH
        
        # Make sure the angle is between -pi and pi
        delta_theta = (delta_theta + math.pi) % (2 * math.pi) - math.pi
        return delta_theta