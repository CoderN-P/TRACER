import numpy as np
from typing import List
from .. import ROBOT_CONFIG
from ..StateEstimation import RobotState
from ..Command import Command, CommandType, MotorCommand, TwistCommand
from .TrajectoryState import TrajectoryState
from .utils import twist_to_wheel_speeds, get_local_target


class RAMSETE:
    def __init__(self, trajectory: List[TrajectoryState]):
        self.trajectory = trajectory
        self.last_index = 0
        self.running_time = 0.0
    
    @staticmethod
    def get_error(current_state: RobotState, target_state: TrajectoryState) -> tuple:
        error_x, error_y = get_local_target(current_state, (target_state.x, target_state.y,))
        error_theta = (target_state.theta - current_state.yaw + np.pi) % (2*np.pi) - np.pi
        return error_x, error_y, error_theta,
    
    def get_target_state(self) -> TrajectoryState:
        while self.last_index < len(self.trajectory) - 1 and self.trajectory[self.last_index].t < self.running_time:
            self.last_index += 1
            
        # Interpolate between the last two trajectory states to get a smoother target state
        if self.last_index == 0:
            return self.trajectory[self.last_index]
    
        prev_state = self.trajectory[self.last_index - 1]
        next_state = self.trajectory[self.last_index]
        dt = max(next_state.t - prev_state.t, 1e-6)
        t_ratio = (self.running_time - prev_state.t) / dt
        
        interp_x = prev_state.x + t_ratio * (next_state.x - prev_state.x)
        interp_y = prev_state.y + t_ratio * (next_state.y - prev_state.y)
        interp_theta = (prev_state.theta + t_ratio * ((next_state.theta - prev_state.theta + np.pi) % (np.pi*2) - np.pi)) % (2*np.pi)
        interp_v = prev_state.v + t_ratio * (next_state.v - prev_state.v)
        interp_omega = prev_state.omega + t_ratio * (next_state.omega - prev_state.omega)
        
        return TrajectoryState(
            x=interp_x,
            y=interp_y,
            theta=interp_theta,
            v=interp_v,
            omega=interp_omega,
            t=self.running_time
        )
        
    
    def calculate_control_command(self, current_state: RobotState, dt: float) -> Command:
        if self.is_complete():
            return Command.stop()
        
        target_state = self.get_target_state()
        error_x, error_y, error_theta = self.get_error(current_state, target_state)
        
        k = 2 * ROBOT_CONFIG.ZETA * np.sqrt(target_state.omega**2 + ROBOT_CONFIG.BETA * target_state.v**2)
        
        v_command = target_state.v * np.cos(error_theta) + k * error_x
        
        sinc = np.sin(error_theta) / error_theta if error_theta > 1e-6 else 1
        
        omega_command = target_state.omega + k * error_theta + ROBOT_CONFIG.BETA * target_state.v * sinc * error_y
        
        self.running_time += dt

        return Command(
            ID="",
            command_type=CommandType.TWIST,
            command=TwistCommand(
                v=v_command,
                omega=omega_command,
            ),
            pause_duration=0,
            duration=0
        )

    def is_complete(self) -> bool:
        return self.running_time >= self.trajectory[-1].t

        
        
        
    
    
