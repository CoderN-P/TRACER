import math
from typing import List

from .RobotState import RobotState
from .Command import Command
from .CommandTypeEnum import CommandType
from .MotorCommand import MotorCommand
from . import ROBOT_CONFIG

class PurePursuit:
    def __init__(self, path: List[tuple]):
        self.path = path
        self.last_found_index = 0 # to prevent the robot from going backwards along the path

    def twist_to_wheel_speeds(self, v, w):
        left = v - (w * ROBOT_CONFIG.WHEEL_BASE / 2.0)
        right = v + (w * ROBOT_CONFIG.WHEEL_BASE / 2.0)
    
        return self.scale_to_max(left, right)
    
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
        
        if min_x <= sol_x_1 <= max_x and min_y <= sol_y_1 <= max_y:
            out.append((sol_x_1, sol_y_1,))

        if min_x <= sol_x_2 <= max_x and min_y <= sol_y_2 <= max_y:
            out.append((sol_x_2, sol_y_2,))
    
        return out
    
    def find_goal_point(self, current_pos) -> tuple | None:
        
        for i in range(self.last_found_index, len(self.path) - 1):
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
                
            if math.dist(goal_point, pt2) < math.dist(current_pos, pt2):
                self.last_found_index = i
                return goal_point
        
        return None # no goal point found
    
    @staticmethod
    def get_local_target(robot_state, goal_point) -> tuple:
        dx = goal_point[0] - robot_state.x
        dy = goal_point[1] - robot_state.y
        
        local_x = math.cos(math.radians(robot_state.yaw)) * dx + math.sin(math.radians(robot_state.yaw)) * dy
        local_y = -math.sin(math.radians(robot_state.yaw)) * dx + math.cos(math.radians(robot_state.yaw)) * dy
        
        return local_x, local_y,
    
    
    @staticmethod
    def scale_to_max(left, right) -> tuple:
        max_speed = max(abs(left), abs(right))
        if max_speed > ROBOT_CONFIG.MAX_LINEAR_VEL:
            scale = ROBOT_CONFIG.MAX_LINEAR_VEL / max_speed
            left *= scale
            right *= scale
        return left, right,
    
    def calculate_control_command(self, robot_state: RobotState) -> Command | None:
        """
        Calculate the control command (linear and angular velocity) based on the current robot state and the path.
        """
        current_pos = (robot_state.x, robot_state.y,)
        goal_point = self.find_goal_point(current_pos)
        
        if not goal_point:
            if math.dist(current_pos, self.path[-1]) < ROBOT_CONFIG.LOOKAHEAD_DISTANCE * 1.5:
                goal_point = self.path[-1]
            else:
                return None # The main loop will fall back to manual control
        
        local_target = self.get_local_target(robot_state, goal_point)
        
        lateral_y = local_target[1]
        
        curvature = 2*lateral_y / (ROBOT_CONFIG.LOOKAHEAD_DISTANCE ** 2)
        
        linear_velocity = ROBOT_CONFIG.MAX_LINEAR_VEL
        angular_velocity = curvature * linear_velocity
        
        motor_speeds = self.twist_to_wheel_speeds(linear_velocity, angular_velocity)
        
        return Command(
            command_type=CommandType.MOTOR,
            command=MotorCommand(
                left_motor=motor_speeds[0],
                right_motor=motor_speeds[1],
             ),
             pause_duration=0,
             duration=0
        )
        
        
       
        
        
        