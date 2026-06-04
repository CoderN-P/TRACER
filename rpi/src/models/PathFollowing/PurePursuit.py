import math, numpy as np
from typing import List
import logging

from .GoToGoal import GoToGoal
from .utils import twist_to_wheel_speeds, get_local_target
from .. import ROBOT_CONFIG, GapNavigator
from ..Command import Command, CommandType, MotorCommand
from ..StateEstimation import RobotState
from ..SensorData import SensorData



"""
Used for hand drawn paths and simple waypoints.
"""

class PurePursuit:
    def __init__(self, path: List[tuple]):
        self.path = path
        self.last_found_index = 0 # to prevent the robot from going backwards along the path
        self.go_to_goal = None


    @classmethod
    def from_xy_points(cls, points: List[dict]) -> 'PurePursuit':
        path = [(point['x'], point['y'],) for point in points]
        return cls(path)
    
    @staticmethod
    def sgn(num):
        return 1 if num >= 0 else -1
    
    def circle_intersection(self, current_pos, pt1, pt2) -> List[tuple]:
        r = ROBOT_CONFIG.LOOKAHEAD_DISTANCE
        x1 = pt1[0] - current_pos[0]
        y1 = pt1[1] - current_pos[1]

        x2 = pt2[0] - current_pos[0]
        y2 = pt2[1] - current_pos[1]
        
        dx = x2 - x1
        dy = y2 - y1
        
        dr = math.hypot(dx, dy)
        D = x1*y2 - x2*y1
        
        discriminant = r**2 * dr**2 - D**2
        
        if discriminant < 0:
            return []
        
        sol_x_1 = current_pos[0] + (D*dy + self.sgn(dy)*dx*math.sqrt(discriminant)) / (dr**2) 
        sol_x_2 = current_pos[0] + (D*dy - self.sgn(dy)*dx*math.sqrt(discriminant)) / (dr**2)
        
        sol_y_1 = current_pos[1] + (-D*dx + abs(dy)*math.sqrt(discriminant)) / (dr ** 2) 
        sol_y_2 = current_pos[1] + (-D*dx - abs(dy)*math.sqrt(discriminant)) / (dr ** 2)
        
        min_x = min(pt1[0], pt2[0])
        max_x = max(pt1[0], pt2[0])
        min_y = min(pt1[1], pt2[1])
        max_y = max(pt1[1], pt2[1])
        
        out = []

        EPS = 1e-6
        
        if min_x - EPS <= sol_x_1 <= max_x + EPS and min_y - EPS <= sol_y_1 <= max_y + EPS:
            out.append((sol_x_1, sol_y_1,))

        if min_x - EPS <= sol_x_2 <= max_x + EPS and min_y - EPS <= sol_y_2 <= max_y + EPS:
            out.append((sol_x_2, sol_y_2,))
    
        return out
    
    def find_goal_point(self, current_pos) -> tuple | None:
        
        for i in range(self.last_found_index, min(self.last_found_index + ROBOT_CONFIG.MAX_SEARCH_POINTS, len(self.path) - 1)):
            pt1 = self.path[i]
            pt2 = self.path[i + 1]
            intersection_pts = self.circle_intersection(current_pos, pt1, pt2)
            
            if len(intersection_pts) == 0: continue
            
            if len(intersection_pts) == 2:
                if math.dist(intersection_pts[0], pt2) < math.dist(intersection_pts[1], pt2):
                    goal_point = intersection_pts[0]
                else:
                    goal_point = intersection_pts[1]
            else:
                goal_point = intersection_pts[0]

            # parameterize the segment
            seg_dx = pt2[0] - pt1[0]
            seg_dy = pt2[1] - pt1[1]
            seg_len_sq = seg_dx**2 + seg_dy**2
            
            if seg_len_sq == 0:
                continue
            
            t_robot = ((current_pos[0] - pt1[0]) * seg_dx + (current_pos[1] - pt1[1]) * seg_dy) / seg_len_sq
            t_goal  = ((goal_point[0]  - pt1[0]) * seg_dx + (goal_point[1]  - pt1[1]) * seg_dy) / seg_len_sq
            
            if t_goal > t_robot:
                self.last_found_index = i
                return goal_point
        
        return None # no goal point found

    def calculate_control_command(self, robot_state: RobotState, sensor_data: SensorData, gap_navigator: GapNavigator, update_gap_navigator: bool) -> Command | None:
        """
        Calculate the control command (linear and angular velocity) based on the current robot state and the path.
        """
        
        current_pos = (robot_state.x, robot_state.y,)

        if math.dist(current_pos, self.path[-1]) <= ROBOT_CONFIG.COMPLETION_THRESHOLD and self.last_found_index >= len(self.path) * 0.9:
            return None
        
        goal_point = self.find_goal_point(current_pos)
        
        if not goal_point:
            if not self.go_to_goal:
                logger = logging.getLogger("RobotManager")
                logger.warning("PurePursuit lost the path")
                self.go_to_goal = GoToGoal(self.path[self.last_found_index +  1])

            return self.go_to_goal.calculate_control_command(robot_state, sensor_data, gap_navigator, update_gap_navigator)
        else:
            if self.go_to_goal:
                logger = logging.getLogger("RobotManager")
                logger.warning("PurePursuit found the path again")
                self.go_to_goal = None
                
        local_target = get_local_target(robot_state, goal_point)
        # Repulsive vector is already in the robot's local frame
        # Only apply lateral force to avoid pushing waypoints behind us
        
        if update_gap_navigator:
            gap_navigator.update(local_target)
            
        lateral_y = local_target[1] + math.tan(gap_navigator.heading_offset()) * math.hypot(*local_target)
        
        curvature = 2*lateral_y / (math.hypot(*local_target) ** 2)
        linear_velocity = ROBOT_CONFIG.MAX_LINEAR_VEL_POS / (1 + ROBOT_CONFIG.K_CURVE * abs(curvature))
        angular_velocity = curvature * linear_velocity 
        
        motor_speeds = twist_to_wheel_speeds(linear_velocity, angular_velocity)
        
        return Command(
            ID="",
            command_type=CommandType.MOTOR,
            command=MotorCommand(
                left_motor=motor_speeds[0],
                right_motor=motor_speeds[1],
             ),
             pause_duration=0,
             duration=0
        )
        
        
       
        
        
        
