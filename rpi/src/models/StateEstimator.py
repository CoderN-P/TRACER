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
        self.wheel_base = 0.21  # Distance between the wheels in meters
        self.wheel_diameter = 0.05  # Diameter of the wheels in meters
        self.last_timestep = None

    def update(self, sensor_data: SensorData):
        # TODO: Install encoders to allow for state estimation
        return


    def estimate_heading(self, sensor_data: SensorData):
        # TODO: Install encoders to allow for state estimation
        return
