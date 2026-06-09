from .. import ROBOT_CONFIG
import math
from typing import List

def get_planning_track_width(curvature: float) -> float:
    """Computes track width based purely on geometry for velocity profiling."""
    return ROBOT_CONFIG.WHEEL_BASE_MAX_MAX - (ROBOT_CONFIG.WHEEL_BASE_MAX - ROBOT_CONFIG.WHEEL_BASE_MIN) * math.exp(-ROBOT_CONFIG.ALPHA * abs(curvature))

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


def twist_to_wheel_speeds(v, omega):
    if abs(v) > 1e-5:
        curvature = omega / v
    else:
        curvature = 0.0  # High curvature limit handles pure spins cleanly

    # 2. Get the exact track width the planner assumed for this specific curve shape
    w_eff = get_planning_track_width(curvature)
    
    left = v - (omega * w_eff / 2.0)
    right = v + (omega * w_eff / 2.0)

    return scale_to_max(left, right)

def get_local_target(robot_state, goal_point) -> List[float]:
    dx = goal_point[0] - robot_state.x
    dy = goal_point[1] - robot_state.y

    local_x = math.cos(robot_state.yaw) * dx + math.sin(robot_state.yaw) * dy
    local_y = -math.sin(robot_state.yaw) * dx + math.cos(robot_state.yaw) * dy

    return [local_x, local_y]

def get_ekf_track_width(v_prev: float, omega_prev: float) -> float:
    """Computes track width based on physical forces felt during the last timestep."""
    lateral_accel = abs(omega_prev * v_prev)
    w_eff = ROBOT_CONFIG.WHEEL_BASE_MIN + ROBOT_CONFIG.K_SCRUB * lateral_accel

    # Strictly bound the output between calibrated limits
    return max(ROBOT_CONFIG.WHEEL_BASE_MIN, min(w_eff, ROBOT_CONFIG.WHEEL_BASE_MAX))