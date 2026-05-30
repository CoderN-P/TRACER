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
        self.lateral_shift = 0
   
    
    def shift_target_apf(self, repulsive_vector: tuple[float, float], target: list[float], sensor_data: SensorData):
        raw_shift = repulsive_vector[0] * ROBOT_CONFIG.K_LIDAR_SHIFT
        raw_shift += (1 / sensor_data.ultrasonic.distance_left) * ROBOT_CONFIG.K_US_SHIFT if 1e-4 < sensor_data.ultrasonic.distance_left <= ROBOT_CONFIG.OBSTACLE_AVOID_THRESHOLD else 0
        raw_shift -= (1 / sensor_data.ultrasonic.distance_right) * ROBOT_CONFIG.K_US_SHIFT if 1e-4 < sensor_data.ultrasonic.distance_right <= ROBOT_CONFIG.OBSTACLE_AVOID_THRESHOLD else 0

        raw_shift = ROBOT_CONFIG.MAX_SHIFT * np.tanh(raw_shift)
        
        self.lateral_shift = ROBOT_CONFIG.OBSTACLE_ALPHA * self.lateral_shift + (1 - ROBOT_CONFIG.OBSTACLE_ALPHA) * raw_shift
        
        return target[0], target[1] + self.lateral_shift # y is lateral relative to robot, so it corresponds to x of repulsive vector
    
    """
    Calculate the control command (linear and angular velocity) based on the current robot state and the goal position.
    """
    def calculate_control_command(self, robot_state: RobotState, repulsive_vector: tuple[float, float], sensor_data: SensorData):
        local_target = get_local_target(robot_state, self.goal_position)
        
        distance_to_goal = math.hypot(local_target[0], local_target[1])
        
        if distance_to_goal < ROBOT_CONFIG.COMPLETION_THRESHOLD:
            return None  # The main loop will stop the robot
        
        shifted_target = self.shift_target_apf(repulsive_vector, local_target, sensor_data)
        
        norm = math.hypot(shifted_target[0], shifted_target[1])

        if norm < 1e-6:
            return None
        
        heading_error = math.atan2(shifted_target[1], shifted_target[0])

        v = ROBOT_CONFIG.MAX_LINEAR_VEL * (1 - np.exp(-ROBOT_CONFIG.K_V * (distance_to_goal ** 1.25)))
        omega = ROBOT_CONFIG.K_OMEGA * heading_error * (1 - np.exp(-ROBOT_CONFIG.K_D * (distance_to_goal ** 1.25)))

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
          
