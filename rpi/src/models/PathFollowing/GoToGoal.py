import math

import numpy as np

from .. import ROBOT_CONFIG
from ..StateEstimation import RobotState
from ..SensorData import SensorData
from ..Command import Command, CommandType, MotorCommand
from .utils import twist_to_wheel_speeds, get_local_target


class GoToGoal:
    def __init__(self, goal_position: tuple):
        self.goal_position = goal_position
        self.omega_shift = 0
   
    
    def shift_omega_apf(self, repulsive_vector: tuple[float, float], sensor_data: SensorData):
        omega_shift = repulsive_vector[0] * ROBOT_CONFIG.K_LIDAR_SHIFT
        omega_shift += (1 / sensor_data.ultrasonic.distance_left) * ROBOT_CONFIG.K_US_SHIFT if 1e-4 < sensor_data.ultrasonic.distance_left <= ROBOT_CONFIG.OBSTACLE_AVOID_THRESHOLD else 0
        omega_shift -= (1 / sensor_data.ultrasonic.distance_right) * ROBOT_CONFIG.K_US_SHIFT if 1e-4 < sensor_data.ultrasonic.distance_right <= ROBOT_CONFIG.OBSTACLE_AVOID_THRESHOLD else 0

        omega_shift = ROBOT_CONFIG.MAX_SHIFT * np.tanh(omega_shift)
        
        if abs(omega_shift) > abs(self.omega_shift):
            self.omega_shift = ROBOT_CONFIG.OBSTACLE_ALPHA * self.omega_shift + (1 - ROBOT_CONFIG.OBSTACLE_ALPHA) * omega_shift
        else:
            self.omega_shift = 0.95 * self.omega_shift + (1 - ROBOT_CONFIG.OBSTACLE_ALPHA) * omega_shift
    
    """
    Calculate the control command (linear and angular velocity) based on the current robot state and the goal position.
    """
    def calculate_control_command(self, robot_state: RobotState, repulsive_vector: tuple[float, float], sensor_data: SensorData):
        local_target = get_local_target(robot_state, self.goal_position)
        
        distance_to_goal = math.hypot(local_target[0], local_target[1])
        
        if distance_to_goal < ROBOT_CONFIG.COMPLETION_THRESHOLD:
            return None  # The main loop will stop the robot

        self.shift_omega_apf(repulsive_vector, sensor_data)
        heading_error = math.atan2(local_target[1], local_target[0])

        v = ROBOT_CONFIG.MAX_LINEAR_VEL * (1 - np.exp(-ROBOT_CONFIG.K_V * (distance_to_goal ** 1.25)))
        omega = ROBOT_CONFIG.K_OMEGA * heading_error * (1 - np.exp(-ROBOT_CONFIG.K_D * (distance_to_goal ** 1.25)))  + self.omega_shift
        
        """
        # causes too much oscillation while going backwards
        
        reverse = False
        
        if abs(heading_error) > math.pi / 2:
            reverse = True
        
            if heading_error > 0:
                heading_error -= math.pi
            else:
                heading_error += math.pi

        if reverse: 
            v *= -1
            omega *= -1
        """
            
        vl, vr = twist_to_wheel_speeds(v, omega)

        return Command(
            ID="",
            command_type=CommandType.MOTOR,
            command=MotorCommand(
                left_motor=vl,
                right_motor=vr,
            ),
            pause_duration=0,
            duration=0
        )
          
