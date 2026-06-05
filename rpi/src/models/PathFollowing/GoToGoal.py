import math

import numpy as np

from .. import ROBOT_CONFIG, GapNavigator, RecoveryState
from ..StateEstimation import RobotState
from ..SensorData import SensorData
from ..Command import Command, CommandType, MotorCommand

from .utils import twist_to_wheel_speeds, get_local_target


class GoToGoal:
    def __init__(self, goal_position: tuple):
        self.goal_position = goal_position
   
    """
    Calculate the control command (linear and angular velocity) based on the current robot state and the goal position.
    """
    def calculate_control_command(self, robot_state: RobotState, sensor_data: SensorData, gap_navigator: GapNavigator, update_gap_navigator: bool):
        local_target = get_local_target(robot_state, self.goal_position)
        
        distance_to_goal = math.hypot(local_target[0], local_target[1])
        
        if distance_to_goal < ROBOT_CONFIG.COMPLETION_THRESHOLD:
            return None  # The main loop will stop the robot

        if update_gap_navigator:
            gap_navigator.update(local_target)

        if gap_navigator.recovery_state == RecoveryState.SCANNING:
            v = 0.0
            # Rotate slowly at 30 degrees/sec scaled to your spin direction parameter
            omega = gap_navigator.spin_direction * 0.5236

        elif gap_navigator.recovery_state == RecoveryState.ALIGNING:
            v = 0.0
            # Use your normal alignment offset math to lock onto the gap center while standing still
            omega = gap_navigator.heading_offset() * 1.5 # Proportional gain booster for snaps

        else:
            # NORMAL TRACKING NAVIGATION MODE
            # If CLEAR, head straight to target. If AVOIDING, head to committed_gap_center.
            heading_offset = gap_navigator.heading_offset()
            heading_error = math.atan2(local_target[1], local_target[0]) + heading_offset
    
            v = ROBOT_CONFIG.MAX_LINEAR_VEL_POS * (1 - np.exp(-ROBOT_CONFIG.K_V * (distance_to_goal ** 1.25)))
    
            omega = ROBOT_CONFIG.K_OMEGA * heading_error * (1 - np.exp(-ROBOT_CONFIG.K_D * (distance_to_goal ** 1.25))) 
        
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
          
