from .. import ROBOT_CONFIG
import math
from typing import List

def scale_to_max(left, right) -> tuple:
    
    if left > 0:
        left_scale = ROBOT_CONFIG.MAX_LINEAR_VEL_POS / left
    elif left < 0:
        left_scale = ROBOT_CONFIG.MAX_LINEAR_VEL_NEG / left
    else:
        left_scale = 1

    if right > 0:
        right_scale = ROBOT_CONFIG.MAX_LINEAR_VEL_POS / right
    elif left < 0:
        right_scale = ROBOT_CONFIG.MAX_LINEAR_VEL_NEG / right
    else:
        right_scale = 1
        
    scale = min(
        left_scale,
        right_scale,
        1
    )

    return max(-ROBOT_CONFIG.MAX_LINEAR_VEL_NEG, min(left * scale, ROBOT_CONFIG.MAX_LINEAR_VEL_POS)),  max(-ROBOT_CONFIG.MAX_LINEAR_VEL_NEG, min(right * scale, ROBOT_CONFIG.MAX_LINEAR_VEL_POS))

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