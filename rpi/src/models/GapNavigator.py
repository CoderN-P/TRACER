from typing import List
import numpy as np, math
from . import ROBOT_CONFIG
from .SensorData.Lidar import LidarGrid
from .Gap import Gap
from .ObstacleState import ObstacleState
from .StateEstimation import RobotState
from .ObstacleMode import ObstacleMode
from .VirtualObstacle import VirtualObstacle

class GapNavigator:
    def __init__(self):
        self.state: ObstacleState = ObstacleState.CLEAR
        self.virtual_obstacles: List[VirtualObstacle] = []
        self.mode: ObstacleMode = ObstacleMode.NORMAL
        self.committed_gap_center: int | None = None  # column index
        self.clear_counter: int = 0
        self.column_depths: np.ndarray = np.array([])
        self.ray_points: List[tuple[float | None, float | None]] = [(None, None)] * ROBOT_CONFIG.GRID_COLS

    def update_grid(self, robot_state: RobotState, grid: LidarGrid | None = None):
        if not grid and self.mode == ObstacleMode.VIRTUAL:
            self.column_depths = self.simulate_lidar(robot_state)
        elif grid:
            self.column_depths = self.get_column_depths(grid)
    
    @staticmethod
    def get_goal_col(local_target: List[float], grid_cols: int, grid_fov: float) -> int:
        # Map local target angle to column index
        goal_angle = math.atan2(local_target[1], local_target[0])
        goal_col = int((goal_angle / (grid_fov / 2) + 1) / 2 * grid_cols)

        offset_angle = math.atan2(ROBOT_CONFIG.LIDAR_OFFSET, local_target[0])
        offset_cols = int((offset_angle / (grid_fov / 2)) * grid_cols)
        goal_col_corrected = goal_col - offset_cols  # shift goal col to account for sensor offset

        return max(0, min(grid_cols - 1, goal_col_corrected))  # clamp to valid range
            
    
    def update(self, local_target: List[float]):
        if len(self.column_depths) == 0: return
        goal_col = self.get_goal_col(local_target, len(self.column_depths), ROBOT_CONFIG.FOV_RAD)
        gaps = self.find_gaps(self.column_depths, ROBOT_CONFIG.OBSTACLE_AVOID_THRESHOLD)
        all_clear = all(d > ROBOT_CONFIG.OBSTACLE_DETECTED_THRESHOLD for d in self.column_depths)

        if self.state == ObstacleState.CLEAR:
            if not all_clear:
                gap = self.select_gap(gaps, self.column_depths, goal_col)
                if gap:
                    self.state = ObstacleState.AVOIDING
                    self.committed_gap_center = gap.center
                    self.clear_counter = 0

        elif self.state == ObstacleState.AVOIDING:
            if all_clear:
                self.clear_counter += 1
                if self.clear_counter > ROBOT_CONFIG.CLEAR_FRAMES_THRESHOLD:  # ~0.5s at 20hz
                    self.state = ObstacleState.CLEAR
                    self.committed_gap_center = None
            else:
                self.clear_counter = 0
                # Update committed gap only if current gap shifted significantly
                gap = self.select_gap(gaps, self.column_depths, goal_col)
                if gap and abs(gap.center - self.committed_gap_center) > ROBOT_CONFIG.GAP_UPDATE_THRESHOLD:
                    self.committed_gap_center = gap.center
    
    @staticmethod
    def get_column_depths(grid: LidarGrid) -> np.ndarray:
        values = np.array(grid.values)  # (rows, cols, 2)
        depth = values[:, :, 1]  # (rows, cols)
        dist = np.linalg.norm(values, axis=2)
    
        valid = (dist > 0) & (depth > 0)
        depth_valid = np.where(valid, depth, np.inf)
    
        return np.min(depth_valid, axis=0)  # (cols,) min depth per column

    @staticmethod
    def min_gap_columns(min_width_m: float, depth: float, grid_cols: int, fov_rad: float) -> int:
        # Angular width needed to fit min_width_m at given depth
        angular_width = 2 * math.atan2(min_width_m / 2, depth)
        # Convert to columns
        return int((angular_width / fov_rad) * grid_cols)
    
   
    def heading_offset(self) -> float:
        # Map column index to lateral angle
        if not self.committed_gap_center or len(self.column_depths) == 0: return 0.0
        
        center_normalized = (self.committed_gap_center / len(self.column_depths)) - 0.5  # -0.5 to 0.5
        angle = center_normalized * ROBOT_CONFIG.FOV_RAD  # in radians
        return angle
    
    @staticmethod
    def find_gaps(column_depths: np.ndarray, threshold: float) -> List[Gap]:
        navigable = column_depths > threshold  # True = passable column
        gaps = []
    
        in_gap = False
        start = 0
        for i, passable in enumerate(navigable):
            if passable and not in_gap:
                start = i
                in_gap = True
            elif not passable and in_gap:
                gaps.append(Gap(start=start, end=i-1, center=(start+i-1)/2))
                in_gap = False
        if in_gap:
            gaps.append(Gap(start=start, end=len(navigable)-1, center=(start+len(navigable)-1)/2))
    
        return gaps

    def select_gap(self, gaps, column_depths, goal_col) -> Gap | None:
        if not gaps:
            return None  # no navigable gap, need to stop/backup

        # Score each gap: prefer gaps toward goal, weighted by width
        best = None
        best_score = float('inf')
    
        for gap in gaps:
            gap_depth = min(column_depths[gap.start:gap.end+1])  # shallowest point in gap
            required_cols = self.min_gap_columns(ROBOT_CONFIG.MIN_GAP_WIDTH, gap_depth, len(column_depths), ROBOT_CONFIG.FOV_RAD)
            width = gap.end - gap.start
            
            if width < required_cols:
                continue  # too narrow
                
            goal_alignment = abs(gap.center - goal_col)
            score = goal_alignment - ROBOT_CONFIG.K_WIDTH * width  # closer to goal and wider = better
            if score < best_score:
                best_score = score
                best = gap
    
        return best

    
    def simulate_lidar_column(self, robot_state: RobotState, col_angle) -> float:
        # Ray direction for this column
        ray_angle = robot_state.yaw + col_angle
        ray_dir = (math.cos(ray_angle), math.sin(ray_angle))
    
        min_dist = np.inf
    
        for obstacle in self.virtual_obstacles:
            dist = obstacle.ray_intersect(robot_state.x, robot_state.y, ray_dir)
            if dist is not None:
                min_dist = min(min_dist, dist)
    
        return min_dist  # inf means no obstacle

    def simulate_lidar(self, robot_state: RobotState) -> np.ndarray:
        column_depths = np.full(ROBOT_CONFIG.GRID_COLS, np.inf)
        self.ray_points = [(None, None)] * ROBOT_CONFIG.GRID_COLS

        for col in range(ROBOT_CONFIG.GRID_COLS):
            col_angle = (col / ROBOT_CONFIG.GRID_COLS - 0.5) * ROBOT_CONFIG.FOV_RAD  # -fov/2 to +fov/2
            column_depths[col] = self.simulate_lidar_column(
                robot_state,
                col_angle
            )
            if column_depths[col] == np.inf:
                self.ray_points[col] = (None, None)
            else:
                self.ray_points[col] = (column_depths[col] * math.cos(col_angle), column_depths[col] * math.sin(col_angle))
        
        self.convert_rays_to_global(robot_state)
        return column_depths
    
    def convert_rays_to_global(self, robot_state: RobotState):
        for i, ray in enumerate(self.ray_points):
            if ray[0] is None: continue
            self.ray_points[i] = (
                robot_state.x + ray[0] * math.cos(robot_state.yaw) - ray[1] * math.sin(robot_state.yaw),
                robot_state.y + ray[0] * math.sin(robot_state.yaw) + ray[1] * math.cos(robot_state.yaw)
            )
            
            
        
