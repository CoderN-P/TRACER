import math
from .RobotState import RobotState
from .SensorData import SensorData
from .HeadingFilter import HeadingFilter
from . import ROBOT_CONFIG


class StateEstimator:
    def __init__(self):
        self.state: RobotState = RobotState(
            x=0.0,
            y=0.0,
            yaw=0.0,
            pitch=0.0,
            roll=0.0,
            linear_velocity=0.0,
            angular_velocity=0.0
        )
        
        self.prev_state: RobotState = self.state.model_copy()
        
        # Pre state estimations
        self.initial_mag_heading = None
        self.theta_encoders = 0.0 # Cumulative heading change from encoders, in radians
        
        self.heading_filter = HeadingFilter()
    
    def initialize(self, sensor_data: SensorData):
        self.initial_mag_heading = math.radians(sensor_data.magnetometer.heading)
        
        
    def reset(self):
        self.state = RobotState(
            x=0.0,
            y=0.0,
            yaw=0.0,
            pitch=0.0, # Not used
            roll=0.0,  # Not used
            linear_velocity=0.0,
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
            dt = (current_time + (4294.967295 - previous_time))  # Handle rollover (4.294967295 seconds for 32-bit microsecond timer)
        else:
            dt = current_time - previous_time
            
        return dt

    @staticmethod
    def estimate_linear_velocity(left_ticks, right_ticks, dt):
        delta_left = left_ticks * ROBOT_CONFIG.METERS_PER_TICK_LEFT
        delta_right = right_ticks * ROBOT_CONFIG.METERS_PER_TICK_RIGHT
        linear_velocity = (delta_left + delta_right) / (2 * dt)
        return linear_velocity
    
    @staticmethod 
    def get_position_delta(left_ticks, right_ticks, heading):
        delta_l = left_ticks * ROBOT_CONFIG.METERS_PER_TICK_LEFT
        delta_r = right_ticks * ROBOT_CONFIG.METERS_PER_TICK_RIGHT
        
        delta_s = ( delta_l + delta_r ) / 2
        
        # Heading must be in radians
        return delta_s * math.cos(heading), delta_s * math.sin(heading),
        
    def update(self, sensor_data: SensorData, previous_sensor_data: SensorData):
        # Previous sensor data is needed to determine dt
        self.prev_state = self.state.model_copy()
        dt = self.calculate_dt(sensor_data.timestamp, previous_sensor_data.timestamp)
        
        delta_left_ticks = sensor_data.left_encoder_ticks - previous_sensor_data.left_encoder_ticks
        delta_right_ticks = sensor_data.right_encoder_ticks - previous_sensor_data.right_encoder_ticks
        
        self.theta_encoders += self.heading_delta_from_encoders(delta_left_ticks, delta_right_ticks)
        
        if sensor_data.magnetometer.new:
            mag_heading_rad = math.radians(sensor_data.magnetometer.heading)
            if self.initial_mag_heading is not None:
                mag_heading_rad -= self.initial_mag_heading
                mag_heading_rad = (mag_heading_rad + math.pi) % (2 * math.pi) - math.pi
            else:
                self.initial_mag_heading = math.radians(sensor_data.magnetometer.heading)
                mag_heading_rad = 0.0
        else:
            mag_heading_rad = None
            
        self.state.yaw = self.heading_filter.step(self.theta_encoders, sensor_data.gyro_z, dt, mag_heading_rad)
    
        
        self.state.linear_velocity = self.estimate_linear_velocity(delta_left_ticks, delta_right_ticks, dt)
        self.state.angular_velocity = ((self.state.yaw - self.prev_state.yaw) % (2 * math.pi) - math.pi) / dt
        
        position_delta_x, position_delta_y = self.get_position_delta(delta_left_ticks, delta_right_ticks, self.state.yaw)
        self.state.x += position_delta_x
        self.state.y += position_delta_y
    
        return
        
        
    @staticmethod
    def heading_delta_from_encoders(left_ticks, right_ticks):
        delta_left = left_ticks * ROBOT_CONFIG.METERS_PER_TICK_LEFT
        delta_right = right_ticks * ROBOT_CONFIG.METERS_PER_TICK_RIGHT
        return (delta_right - delta_left) / ROBOT_CONFIG.WHEEL_BASE_WIDTH