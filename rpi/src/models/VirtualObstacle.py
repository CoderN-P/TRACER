from pydantic import Field, BaseModel
import math
from . import RobotState, ROBOT_CONFIG
from .VirtualObstacleType import VirtualObstacleType

class VirtualObstacle(BaseModel):
    obstacle_type: VirtualObstacleType = Field(default=VirtualObstacleType.CIRCLE, description="Obstacle type (rectangle/circle)")
    position: tuple[float, float] = Field(default_factory=lambda: (0, 0,), description="XY position of the center of the obstacle in meters")
    rotation: float | None = Field(default=None, description="Rotation of the virtual obstacle in radians")
    width: float | None = Field(default=None, description="Width of the rectangular obstacle in meters")
    height: float | None = Field(default=None, description="Height of the rectangular obstacle in meters")
    radius: float | None = Field(default=None, description="Radius of the circular obstacle in meters")


    def closest_rect_pos(self, robot_state: RobotState):
        # --- STEP 1: Transform Rectangle Center to Robot Local Frame ---
        dx = self.position[0] - robot_state.x
        dy = self.position[1] - robot_state.y 
    
        # Negative theta to un-rotate the robot's orientation
        cos_t = math.cos(robot_state.yaw)
        sin_t = math.sin(robot_state.yaw)
    
        rect_local_x = dx * cos_t + dy * sin_t
        rect_local_y = -dx * sin_t + dy * cos_t
        rect_local_alpha = self.rotation - robot_state.yaw
    
        # --- STEP 2: Find Closest Point to Robot (0, 0) in Robot Frame ---
        # To do this, we treat rect_local as our target, and un-rotate *it* to axis-aligned
        cos_a = math.cos(-rect_local_alpha)
        sin_a = math.sin(-rect_local_alpha)
    
        # Translate robot (0,0) relative to local rect center, then un-rotate
        rel_robot_x = 0.0 - rect_local_x
        rel_robot_y = 0.0 - rect_local_y
    
        unrotated_robot_x = rel_robot_x * cos_a - rel_robot_y * sin_a
        unrotated_robot_y = rel_robot_x * sin_a + rel_robot_y * cos_a
    
        # Clamp to the rectangle's half-dimensions
        half_w = self.width / 2.0
        half_h = self.height / 2.0
        clamped_x = max(-half_w, min(unrotated_robot_x, half_w))
        clamped_y = max(-half_h, min(unrotated_robot_y, half_h))
    
        # Rotate clamped point back to the rectangle's local orientation
        cos_a_fwd = math.cos(rect_local_alpha)
        sin_a_fwd = math.sin(rect_local_alpha)
    
        closest_local_x = clamped_x * cos_a_fwd - clamped_y * sin_a_fwd + rect_local_x
        closest_local_y = clamped_x * sin_a_fwd + clamped_y * cos_a_fwd + rect_local_y
    
        return closest_local_x, closest_local_y


    def closest_circle_pos(self, robot_state: RobotState):
        # --- STEP 1: Transform Circle Center to Robot Local Frame ---
        dx = self.position[0] - robot_state.x
        dy = self.position[1] - robot_state.y
    
        cos_t = math.cos(robot_state.yaw)
        sin_t = math.sin(robot_state.yaw)
    
        # Circle center coordinates in the robot's local frame
        circle_local_x = dx * cos_t + dy * sin_t
        circle_local_y = -dx * sin_t + dy * cos_t
    
        # --- STEP 2: Find Closest Point on Perimeter to Robot (0,0) ---
        # Calculate distance from robot (0,0) to circle center
        distance_to_center = math.hypot(circle_local_x, circle_local_y)
    
        # Edge case: Robot is exactly at the center of the circle
        if distance_to_center < 1e-9:
            return self.radius, 0.0  # Return a point on the perimeter directly ahead of the robot
    
        # Vector pointing from circle center to robot (0,0)
        # This direction is simply the negative of the center's position vector
        dir_x = -circle_local_x / distance_to_center
        dir_y = -circle_local_y / distance_to_center
    
        # Move from the circle center along that unit vector by radius r
        closest_local_x = circle_local_x + dir_x * self.radius
        closest_local_y = circle_local_y + dir_y * self.radius
    
        return closest_local_x, closest_local_y


    def beam_distances_to_circle(self, robot_state: RobotState):
        # 1. Transform Circle Center to Robot Local Frame
        dx = self.position[0] - robot_state.x
        dy = self.position[1] - robot_state.y
        cos_t = math.cos(robot_state.yaw)
        sin_t = math.sin(robot_state.yaw)
    
        circle_local_x = dx * cos_t + dy * sin_t
        circle_local_y = -dx * sin_t + dy * cos_t
    
        # 2. Define angles for Left (+45) and Right (-45) beams
        left_angle = math.pi / 4.0
        right_angle = -math.pi / 4.0
    
        lensq_c = circle_local_x**2 + circle_local_y**2
    
        distances = []
        for angle in [left_angle, right_angle]:
            rdx = math.cos(angle)
            rdy = math.sin(angle)
    
            # Ray-Circle Quadratic Formulation
            dot_dc = rdx * circle_local_x + rdy * circle_local_y
            discriminant = dot_dc**2 - lensq_c + self.radius**2
    
            if discriminant < 0:
                distances.append(float('inf'))
                continue
    
            sqrt_disc = math.sqrt(discriminant)
            t1 = dot_dc - sqrt_disc
            t2 = dot_dc + sqrt_disc
    
            if t1 >= 0:
                distances.append(t1)
            elif t2 >= 0:
                distances.append(t2)  # Robot is inside the circle
            else:
                distances.append(float('inf')) # Circle is behind this beam direction
    
        return distances[0], distances[1] # returns (left_dist, right_dist)


    def beam_distances_to_rectangle(self, robot_state: RobotState):
        # 1. Transform the rectangle into the Robot's frame
        dx = self.position[0] - robot_state.x
        dy = self.position[1] - robot_state.y
        cos_t = math.cos(robot_state.yaw)
        sin_t = math.sin(robot_state.yaw)
    
        rect_local_x = dx * cos_t + dy * sin_t
        rect_local_y = -dx * sin_t + dy * cos_t
        rect_local_alpha = self.rotation - robot_state.yaw
    
        # 2. Setup Ray Origin relative to Rectangle Alignment
        tx = -rect_local_x
        ty = -rect_local_y
        cos_a = math.cos(-rect_local_alpha)
        sin_a = math.sin(-rect_local_alpha)
    
        # Ray origin inside the rectangle's local frame
        ox = tx * cos_a - ty * sin_a
        oy = tx * sin_a + ty * cos_a
    
        hw, hh = self.width / 2.0, self.height / 2.0
        left_angle = math.pi / 4.0
        right_angle = -math.pi / 4.0
    
        distances = []
        for angle in [left_angle, right_angle]:
            # Beam ray directions in robot frame
            rdx = math.cos(angle)
            rdy = math.sin(angle)
    
            # Rotate ray direction into rectangle frame
            dx_rect = rdx * cos_a - rdy * sin_a
            dy_rect = rdx * sin_a + rdy * cos_a
    
            # Slab Method X-axis bounds check
            if abs(dx_rect) < 1e-9:
                if ox < -hw or ox > hw:
                    distances.append(float('inf'))
                    continue
                txmin, txmax = float('-inf'), float('inf')
            else:
                t1 = (-hw - ox) / dx_rect
                t2 = (hw - ox) / dx_rect
                txmin, txmax = min(t1, t2), max(t1, t2)
    
            # Slab Method Y-axis bounds check
            if abs(dy_rect) < 1e-9:
                if oy < -hh or oy > hh:
                    distances.append(float('inf'))
                    continue
                tymin, tymax = float('-inf'), float('inf')
            else:
                t1 = (-hh - oy) / dy_rect
                t2 = (hh - oy) / dy_rect
                tymin, tymax = min(t1, t2), max(t1, t2)
    
            # Overlap intervals
            tnear = max(txmin, tymin)
            tfar = min(txmax, tymax)
    
            # Evaluate intersection valid conditions
            if tnear <= tfar and tfar >= 0:
                distances.append(tnear if tnear >= 0 else tfar)
            else:
                distances.append(float('inf'))
    
        return distances[0], distances[1] # returns (left_dist, right_dist)

    def get_ultrasonic_distance(self, robot_state: RobotState):
        if self.obstacle_type == VirtualObstacleType.RECTANGLE:
            left_dist, right_dist = self.beam_distances_to_rectangle(robot_state)
        elif self.obstacle_type == VirtualObstacleType.CIRCLE:
            left_dist, right_dist = self.beam_distances_to_circle(robot_state)
        else:
            return float('inf'), float('inf')
        
        return left_dist, right_dist

    def get_repulsive_vector(self, robot_state: RobotState):
        dist = math.hypot(self.position[0] - robot_state.x, self.position[1] - robot_state.y)
        
        if self.obstacle_type == VirtualObstacleType.RECTANGLE:
            depth, lateral = self.closest_rect_pos(robot_state)
        elif self.obstacle_type == VirtualObstacleType.CIRCLE:
            depth, lateral = self.closest_circle_pos(robot_state)
        else:
            return 0, 0

        if depth <= 0:
            return 0, 0

        if depth < ROBOT_CONFIG.OBSTACLE_AVOID_THRESHOLD/100.0:
            magnitude = ROBOT_CONFIG.K_REPULSIVE_HARD * (1.0 / depth - 1.0 / (ROBOT_CONFIG.OBSTACLE_AVOID_THRESHOLD/100.0))
        else:
            magnitude = ROBOT_CONFIG.K_REPULSIVE_SOFT * (1.0 / depth - 1.0 / (ROBOT_CONFIG.OBSTACLE_DETECTED_THRESHOLD/100.0))

        magnitude *= depth/dist
        
        return -(lateral/dist) * magnitude, -(depth/dist) * magnitude