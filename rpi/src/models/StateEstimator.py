from .RobotState import RobotState
from .SensorData import SensorData


class StateEstimator:
    def __init__(self, alpha: float = 0.98):
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
        self.alpha = alpha  # Complementary filter coefficient
    
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
            
        
    def update(self, sensor_data: SensorData, previous_sensor_data: SensorData):
        # Previous sensor data is needed to determine 
        # TODO: Install encoders to allow for state estimation
        return


    def estimate_heading(self, sensor_data: SensorData):
        # TODO: Install encoders to allow for state estimation
        return
