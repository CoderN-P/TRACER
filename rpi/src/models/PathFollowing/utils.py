from .. import ROBOT_CONFIG
import math
from typing import List

def scale_to_max(left, right) -> tuple:
    
    
    scale = min(
        ROBOT_CONFIG.MAX_LINEAR_VEL / abs(left) if left > 1e-04 else 1,
        ROBOT_CONFIG.MAX_LINEAR_VEL / abs(right) if right > 1e-04 else 1,
        1
    )

    return max(-ROBOT_CONFIG.MAX_LINEAR_VEL, min(left * scale, ROBOT_CONFIG.MAX_LINEAR_VEL)),  max(-ROBOT_CONFIG.MAX_LINEAR_VEL, min(right * scale, ROBOT_CONFIG.MAX_LINEAR_VEL))

def twist_to_wheel_speeds(v, w):
    left = v - (w * ROBOT_CONFIG.WHEEL_BASE / 2.0)
    right = v + (w * ROBOT_CONFIG.WHEEL_BASE / 2.0)

    return scale_to_max(left, right)

def get_local_target(robot_state, goal_point) -> List[float]:
    dx = goal_point[0] - robot_state.x
    dy = goal_point[1] - robot_state.y

    local_x = math.cos(robot_state.yaw) * dx + math.sin(robot_state.yaw) * dy
    local_y = -math.sin(robot_state.yaw) * dx + math.cos(robot_state.yaw) * dy

    return [local_x, local_y]