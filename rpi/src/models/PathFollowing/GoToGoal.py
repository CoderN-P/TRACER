import math

import numpy as np

from .. import ROBOT_CONFIG
from ..StateEstimation import RobotState
from ..Command import Command, CommandType, MotorCommand
from .PurePursuit import PurePursuit


class GoToGoal:
    def __init__(self, goal_position: tuple):
        self.goal_position = goal_position
        
    """
    Calculate the control command (linear and angular velocity) based on the current robot state and the goal position.
    Implements a simple trapezoidal velocity profile to smoothly approach the goal, and a proportional controller for angular velocity to face the goal.
    """
  
    def calculate_control_command(self, robot_state: RobotState, repulsive_vector: tuple[float, float]):
        local_target = PurePursuit.get_local_target(robot_state, self.goal_position)
        
        distance_to_goal = math.hypot(local_target[0], local_target[1])
        
        if distance_to_goal < ROBOT_CONFIG.COMPLETION_THRESHOLD:
            return None  # The main loop will stop the robot
        
        att_x = ROBOT_CONFIG.K_ATTRACTIVE * local_target[0]
        att_y = ROBOT_CONFIG.K_ATTRACTIVE * local_target[1]
        
        combined_x = att_x + repulsive_vector[1] # x is vertical relative to robot, so it corresponds to y of repulsive vector
        combined_y = att_y + repulsive_vector[0] # y is lateral relative to robot, so it corresponds to x of repulsive vector

        norm = math.hypot(combined_x, combined_y)

        if norm < 1e-6:
            return None
        
        heading_error = math.atan2(combined_y, combined_x)

        v = ROBOT_CONFIG.MAX_LINEAR_VEL * (1 - np.exp(-ROBOT_CONFIG.K_V * distance_to_goal))
        omega = ROBOT_CONFIG.K_OMEGA * heading_error * (1 - np.exp(-ROBOT_CONFIG.K_D * distance_to_goal))
        
        vl, vr = PurePursuit.twist_to_wheel_speeds(v, omega)

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
          