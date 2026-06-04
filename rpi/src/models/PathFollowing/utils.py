from .. import ROBOT_CONFIG
import math
from typing import List

def scale_to_max(left, right) -> tuple:
    abs_left = abs(left)
    abs_right = abs(right)
    
    # 1. Assign the correct positive threshold based on intended wheel direction
    left_limit = ROBOT_CONFIG.MAX_LINEAR_VEL_POS if left >= 0 else ROBOT_CONFIG.MAX_LINEAR_VEL_NEG
    right_limit = ROBOT_CONFIG.MAX_LINEAR_VEL_POS if right >= 0 else ROBOT_CONFIG.MAX_LINEAR_VEL_NEG
    
    # 2. Calculate scaling factors using absolute magnitudes to prevent sign flips
    left_scale = left_limit / abs_left if abs_left > 0 else 1.0
    right_scale = right_limit / abs_right if abs_right > 0 else 1.0
    
    # 3. Find the uniform scale down factor
    scale = min(left_scale, right_scale, 1.0)
    
    # 4. Apply scale safely
    scaled_left = left * scale
    scaled_right = right * scale
    
    # 5. Clamp using the correct dynamic limits (negating the limit for backward motion)
    final_left = max(-ROBOT_CONFIG.MAX_LINEAR_VEL_NEG, min(scaled_left, ROBOT_CONFIG.MAX_LINEAR_VEL_POS))
    final_right = max(-ROBOT_CONFIG.MAX_LINEAR_VEL_NEG, min(scaled_right, ROBOT_CONFIG.MAX_LINEAR_VEL_POS))
    
    return final_left, final_right


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
