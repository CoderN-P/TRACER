from pydantic import Field, BaseModel
import math, numpy as np
from .VirtualObstacleType import VirtualObstacleType
from .StateEstimation import RobotState

class VirtualObstacle(BaseModel):
    obstacle_type: VirtualObstacleType = Field(default=VirtualObstacleType.CIRCLE, description="Obstacle type (rectangle/circle)")
    position: tuple[float, float] = Field(default_factory=lambda: (0, 0,), description="XY position of the center of the obstacle in meters")
    rotation: float | None = Field(default=None, description="Rotation of the virtual obstacle in radians")
    width: float | None = Field(default=None, description="Width of the rectangular obstacle in meters")
    height: float | None = Field(default=None, description="Height of the rectangular obstacle in meters")
    radius: float | None = Field(default=None, description="Radius of the circular obstacle in meters")


    def ray_intersect_rect(self, ray_origin, ray_dir) -> float | None:
        # Transform ray into rectangle's local frame
        cos_a = math.cos(-self.rotation)
        sin_a = math.sin(-self.rotation)
    
        # Translate ray origin relative to rect center
        ox = ray_origin[0] - self.position[0]
        oy = ray_origin[1] - self.position[1]
    
        # Rotate into rect local frame
        local_ox = ox * cos_a - oy * sin_a
        local_oy = ox * sin_a + oy * cos_a
        local_dx = ray_dir[0] * cos_a - ray_dir[1] * sin_a
        local_dy = ray_dir[0] * sin_a + ray_dir[1] * cos_a
    
        # Now it's axis-aligned, use slab method
        dx = 1/local_dx if abs(local_dx) > 1e-9 else np.inf
        dy = 1/local_dy if abs(local_dy) > 1e-9 else np.inf
    
        tx1 = (-self.width/2 - local_ox) * dx
        tx2 = ( self.width/2 - local_ox) * dx
        ty1 = (-self.height/2 - local_oy) * dy
        ty2 = ( self.height/2 - local_oy) * dy
    
        tmin = max(min(tx1, tx2), min(ty1, ty2))
        tmax = min(max(tx1, tx2), max(ty1, ty2))
    
        if tmax < 0 or tmin > tmax:
            return None
        return tmin if tmin > 0 else tmax


    def ray_intersect_circle(self, ray_origin, ray_dir) -> float | None:
        # Vector from ray origin to circle center
        oc = (ray_origin[0] - self.position[0], ray_origin[1] - self.position[1])
    
        a = ray_dir[0]**2 + ray_dir[1]**2
        b = 2 * (oc[0]*ray_dir[0] + oc[1]*ray_dir[1])
        c = oc[0]**2 + oc[1]**2 - self.radius**2
    
        discriminant = b**2 - 4*a*c
        if discriminant < 0:
            return None
    
        t = (-b - math.sqrt(discriminant)) / (2*a)
        return t if t > 0 else None


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

    def ray_intersect(self, ray_origin_x, ray_origin_y, ray_dir):
        ray_origin = [ray_origin_x, ray_origin_y] 
        if self.obstacle_type == VirtualObstacleType.CIRCLE:
            return self.ray_intersect_circle(ray_origin, ray_dir)
        else:
            return self.ray_intersect_rect(ray_origin, ray_dir)
    
