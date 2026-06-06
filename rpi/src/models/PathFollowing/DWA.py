from typing import List
import math, numpy as np
from shapely.geometry import box
from shapely.affinity import rotate
from .utils import twist_to_wheel_speeds
from ..Command import Command, CommandType, MotorCommand
from ..StateEstimation import RobotState
from ..VirtualObstacle import VirtualObstacle
from ..VirtualObstacleType import VirtualObstacleType
from .. import ROBOT_CONFIG

class DWA:
    def __init__(self, goal_position: tuple, virtual_obstacles: List[VirtualObstacle]):  
        self.goal_position = goal_position
        self.virtual_obstacles = virtual_obstacles
        
    def calculate_control_command(self, robot_state: RobotState):
        if math.hypot(robot_state.x - self.goal_position[0], robot_state.y - self.goal_position[1]) <= ROBOT_CONFIG.COMPLETION_THRESHOLD:
            return None
        
        v_min, v_max, omega_min, omega_max = self.find_dynamic_window(robot_state)
        candidate_v = np.linspace(v_min, v_max, ROBOT_CONFIG.V_SAMPLES)
        candidate_omega = np.linspace(omega_min, omega_max, ROBOT_CONFIG.OMEGA_SAMPLES)
        
        best_score = 0
        best_v = robot_state.v
        best_omega = robot_state.omega
        
        for v in candidate_v:
            for omega in candidate_omega:
                trajectory = self.simulate_trajectory(robot_state, v, omega)
                min_dist = self.distance(trajectory)
                
                stopping_dist = v*v/(2*ROBOT_CONFIG.MAX_LONG_ACCEL)
                
                # Restrict search space to admissible velocities
                if stopping_dist < min_dist:
                    continue
                    
                score = ROBOT_CONFIG.DWA_SIGMA * (
                    ROBOT_CONFIG.DWA_ALPHA * self.heading(v, omega, robot_state) +
                    ROBOT_CONFIG.DWA_BETA * min_dist +
                    ROBOT_CONFIG.DWA_Y * self.velocity(v)
                )
                
                if score > best_score:
                    best_v = v
                    best_omega = omega

        vl, vr = twist_to_wheel_speeds(best_v, best_omega)

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
    
    @staticmethod
    def find_dynamic_window(robot_state: RobotState):
        # Calculate the dynamic window based on current velocity and acceleration limits
        dt = 1 / ROBOT_CONFIG.CHECK_OBSTACLE_FREQ
        v_min = max(0, robot_state.v - ROBOT_CONFIG.MAX_LONG_ACCEL * dt)
        v_max = min(ROBOT_CONFIG.MAX_LINEAR_VEL_POS, robot_state.v + ROBOT_CONFIG.MAX_LONG_ACCEL * dt)
        omega_min = max(-ROBOT_CONFIG.MAX_ALPHA, robot_state.omega - ROBOT_CONFIG.MAX_ALPHA * dt)
        omega_max = min(ROBOT_CONFIG.MAX_ALPHA, robot_state.omega + ROBOT_CONFIG.MAX_ALPHA * dt)
        
        return v_min, v_max, omega_min, omega_max
    
    @staticmethod
    def simulate_trajectory(robot_state: RobotState, v, omega):
        trajectory = []

        x = robot_state.x
        y = robot_state.y
        theta = robot_state.theta
        
        dt = 1 / ROBOT_CONFIG.CHECK_OBSTACLE_FREQ
        for _ in range(ROBOT_CONFIG.DWA_STEPS):
            x += v * math.cos(theta) * dt
            y += v * math.sin(theta) * dt
            theta += omega * dt
        
            trajectory.append((x, y, theta))
        
        return trajectory
    
    def distance(self, trajectory):
        dist = 0
        for i in range(1, len(trajectory)):
            x, y, theta = trajectory[i]
            dist += math.hypot(x - trajectory[i-1][0], y - trajectory[i - 1][1])
            collision = False
            
            for obstacle in self.virtual_obstacles:
                if obstacle.obstacle_type == VirtualObstacleType.CIRCLE:
                    collision = self.check_collision_circle(x, y, theta, obstacle.position[0], obstacle.position[1], obstacle.radius)
                else:
                    collision = self.check_collision_rect(x, y, theta, obstacle.position[0], obstacle.position[1],obstacle.width, obstacle.height, obstacle.rotation)
                    
            if collision:
                return dist
        
        return 300
        
        
    @staticmethod
    def check_collision_rect(x, y, theta, a, b, w, h, rot):
        # 1. Create unrotated bounding boxes centered at (0,0)
        rw = ROBOT_CONFIG.ROBOT_WIDTH
        rh = ROBOT_CONFIG.ROBOT_HEIGHT
        
        b1 = box(-rw/2, -rh/2, rw/2, rh/2)
        b2 = box(-w/2, -h/2, w/2, h/2)
    
        # 2. Rotate them around their centers and shift to true coordinates
        rect1 = rotate(b1, theta, origin=(0, 0), use_radians=True)
        rect1 = rotate(rect1, 0, origin=(-x, -y), use_radians=True) # Fast offset transformation
    
        rect2 = rotate(b2, rot, origin=(0, 0), use_radians=True)
        rect2 = rotate(rect2, 0, origin=(-a, -b), use_radians=True)
    
        # 3. Check for geometric overlap
        return rect1.intersects(rect2)
    
        
    @staticmethod 
    def check_collision_circle(x, y, theta, a, b, r):
        dx = a - x
        dy = b - y
        
        local_x = dx * math.cos(theta) + dy * math.sin(theta)
        local_y = -dx * math.sin(theta) + dy * math.cos(theta)

        rw = ROBOT_CONFIG.ROBOT_WIDTH
        rh = ROBOT_CONFIG.ROBOT_HEIGHT
        
        closest_x = min(max(local_x, -rw/2), rw/2)
        closest_y = min(max(local_y, -rh/2), rh/2)

        dist_sq = (
            (local_x - closest_x)**2 +
            (local_y - closest_y)**2
        )
    
        return dist_sq <= r*r

    def heading(self, v, omega, robot_state: RobotState):
        v_stop = v
        omega_stop = omega
        
        x = robot_state.x
        y = robot_state.y
        theta = robot_state.theta
        
        dt = 1 / ROBOT_CONFIG.CHECK_OBSTACLE_FREQ
        
        while v_stop > 0:
            x += v_stop * math.cos(theta) * dt
            y += v_stop * math.sin(theta) * dt
            theta += omega_stop * dt
        
            v_stop -= ROBOT_CONFIG.MAX_LONG_ACCEL * dt
        
            omega_stop = self.move_towards(
                omega_stop,
                0,
                ROBOT_CONFIG.MAX_ALPHA * dt
            )

        goal_angle = math.atan2(
            self.goal_position[1] - y,
            self.goal_position[0] - x
        )

        theta = abs(
            self.wrap_angle(goal_angle - theta)
        ) * 180 / math.pi
        
        return 180 - theta
        
    @staticmethod
    def move_towards(current, target, max_delta):
        if abs(target - current) <= max_delta:
            return target
        return current + math.copysign(max_delta, target - current)
    
    @staticmethod
    def wrap_angle(angle):
        while angle > math.pi:
            angle -= 2 * math.pi
        while angle < -math.pi:
            angle += 2 * math.pi
        return angle
        
    @staticmethod
    def velocity(v):
        return v / ROBOT_CONFIG.MAX_LINEAR_VEL_POS
        
    