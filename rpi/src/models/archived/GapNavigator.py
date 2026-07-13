from typing import List
import numpy as np, math
from . import ROBOT_CONFIG
from .SensorData.IPhoneLidar import LidarGrid
from .Gap import Gap
from .ObstacleState import ObstacleState
from .StateEstimation import RobotState
from .ObstacleMode import ObstacleMode
from .VirtualObstacle import VirtualObstacle
from .RecoveryState import RecoveryState


class GapNavigator:
    def __init__(self):
        self.state: ObstacleState = ObstacleState.CLEAR
        self.recovery_state: RecoveryState = RecoveryState.TRACKING # "TRACKING", "SCANNING", "ALIGNING"
        self.spin_direction: int = 1          # 1 = Left (CCW), -1 = Right (CW)
        self.virtual_obstacles: List[VirtualObstacle] = []
        self.mode: ObstacleMode = ObstacleMode.NORMAL
        self.committed_gap_center: float | None = None  # modified to float for precision centering
        self.clear_counter: int = 0
        self.column_depths: np.ndarray = np.array([])
        self.ray_points: List[tuple[float | None, float | None]] = [(None, None)] * ROBOT_CONFIG.GRID_COLS

    def update_grid(self, robot_state: RobotState, grid: LidarGrid | None = None):
        if not grid and self.mode == ObstacleMode.VIRTUAL:
            self.column_depths = self.simulate_lidar(robot_state)
        elif grid:
            self.column_depths = self.get_column_depths(grid)
            self.ray_points = [(None, None)] * ROBOT_CONFIG.GRID_COLS
            
            for i, depth in enumerate(self.column_depths):
                if depth > ROBOT_CONFIG.OBSTACLE_DETECTED_THRESHOLD:
                    continue

                col_angle = (i / ROBOT_CONFIG.GRID_COLS - 0.5) * ROBOT_CONFIG.FOV_RAD
                self.ray_points[i] = (self.column_depths[i] * math.cos(col_angle), self.column_depths[i] * math.sin(col_angle))
                
            self.convert_rays_to_global(robot_state)


    @staticmethod
    def get_goal_col(local_target: List[float], grid_cols: int, grid_fov: float) -> int:
        # Map local target angle to column index
        goal_angle = math.atan2(local_target[1], local_target[0])
        goal_col = int((goal_angle / (grid_fov / 2) + 1) / 2 * grid_cols)

        offset_angle = math.atan2(ROBOT_CONFIG.LIDAR_OFFSET, local_target[0])
        offset_cols = int((offset_angle / (grid_fov / 2)) * grid_cols)
        goal_col_corrected = goal_col - offset_cols  # shift goal col to account for sensor offset

        return goal_col_corrected


    def update(self, local_target: List[float]):
        if len(self.column_depths) == 0: return

        # Calculate raw un-clamped goal column for tracking orientation
        goal_col = self.get_goal_col(local_target, len(self.column_depths), ROBOT_CONFIG.FOV_RAD)
        gaps = self.find_gaps(self.column_depths, ROBOT_CONFIG.OBSTACLE_AVOID_THRESHOLD)
        all_clear = all(d > ROBOT_CONFIG.OBSTACLE_DETECTED_THRESHOLD for d in self.column_depths)

        # Clear recovery state whenever the scanner sees smooth sailing ahead
        if all_clear:
            self.recovery_state = RecoveryState.TRACKING

        if self.state == ObstacleState.CLEAR:
            if not all_clear:
                gap = self.select_gap(gaps, self.column_depths, goal_col)
                if gap:
                    self.state = ObstacleState.AVOIDING
                    self.committed_gap_center = gap.center
                    self.clear_counter = 0
                elif self.recovery_state == RecoveryState.SCANNING:
                    # Force routing system into avoiding constraints during spins
                    self.state = ObstacleState.AVOIDING
                    self.committed_gap_center = None

        elif self.state == ObstacleState.AVOIDING:
            if all_clear:
                self.clear_counter += 1
                if self.clear_counter > ROBOT_CONFIG.CLEAR_FRAMES_THRESHOLD:  # 10 frames = ~0.5s at 20hz
                    self.state = ObstacleState.CLEAR
                    self.committed_gap_center = None
            else:
                self.clear_counter = 0
                gap = self.select_gap(gaps, self.column_depths, goal_col)

                if self.recovery_state == RecoveryState.SCANNING:
                    # While spinning, override forward motion target
                    self.committed_gap_center = None
                elif gap:
                    # Normal tracking/aligning gap update rules
                    if self.committed_gap_center is None or abs(gap.center - self.committed_gap_center) > ROBOT_CONFIG.GAP_UPDATE_THRESHOLD:
                        self.committed_gap_center = gap.center


    def select_gap(self, gaps, column_depths, goal_col) -> Gap | None:
        # Check center of frame (index 32 for 64-col setup)
        center_col = len(column_depths) / 2
        goal_is_left = goal_col >= center_col

        # --- STATE 1: NORMAL TRACKING ---
        if self.recovery_state == RecoveryState.TRACKING:
            if not gaps:
                # Blind valley encountered! Initiate Recovery Spin
                self.recovery_state = RecoveryState.ALIGNING
                self.spin_direction = 1 if goal_is_left else -1
                return None

            valid_gaps = []
            for gap in gaps:
                # CHANGED: Using nanmedian window to stop noise from crushing  gap depth metric
                gap_depth = np.nanmedian(column_depths[gap.start:gap.end+1])
                required_cols = self.min_gap_columns(ROBOT_CONFIG.MIN_GAP_WIDTH, gap_depth, len(column_depths), ROBOT_CONFIG.FOV_RAD)
                width = gap.end - gap.start + 1

                if width >= required_cols:
                    valid_gaps.append((gap, width))

            if not valid_gaps:
                print(gaps)
                # Gaps exist but none are wide enough to fit physical robot bounds
                self.recovery_state = RecoveryState.SCANNING
                self.spin_direction = 1 if goal_is_left else -1
                return None

            # Score each available valid gap
            best = None
            best_score = float('inf')
            for gap, width in valid_gaps:
                goal_alignment = abs(gap.center - goal_col)
                score = goal_alignment - ROBOT_CONFIG.K_WIDTH * width
                if score < best_score:
                    best_score = score
                    best = gap
            return best

        # --- STATE 2: RECOVERY SPIN (SCANNING) ---
        elif self.recovery_state == RecoveryState.SCANNING:
            if not gaps:
                return None

            for gap in gaps:
                gap_depth = np.nanmedian(column_depths[gap.start:gap.end+1])
                required_cols = self.min_gap_columns(ROBOT_CONFIG.MIN_GAP_WIDTH, gap_depth, len(column_depths), ROBOT_CONFIG.FOV_RAD)
                width = gap.end - gap.start + 1

                # HYSTERESIS: Requires gap to be 3 columns wider than minimum width to clear the spin safely
                if width >= (required_cols + 3):
                    self.recovery_state = RecoveryState.ALIGNING
                    return gap
            return None

        # --- STATE 3: ALIGNING TO NEW GAP ---
        elif self.recovery_state == RecoveryState.ALIGNING:
            if not gaps:
                self.recovery_state = RecoveryState.SCANNING
                return None

            # Grab whichever gap is closest to centering our lens frame
            center_col = len(column_depths) / 2
            center_gap = min(gaps, key=lambda g: abs(g.center - center_col))

            # Once the target center drifts within 4 degrees of camera focus, return to normal tracking
            if abs(center_gap.center - center_col) < 4.0:
                self.recovery_state = RecoveryState.TRACKING

            return center_gap

        return None


    @staticmethod
    def get_column_depths(grid: LidarGrid) -> np.ndarray:
        depth = np.array(grid.values)  # Shape is already (rows, cols)

        v_fov_rad = np.radians(48.0)
        v_step_rad = v_fov_rad / 48.0
        phi_angles = - (v_fov_rad / 2.0) + (np.arange(48) * v_step_rad) + (v_step_rad / 2.0)

        # Reshape phi angles to a column vector (48, 1) so it broadcasts across all 64 columns
        phi_grid = phi_angles[:, np.newaxis]

        # 3. Calculate physical height of every pixel relative to the ground
        height_grid = (depth * np.sin(phi_grid)) + ROBOT_CONFIG.LIDAR_HEIGHT

        # 4. Create a mask for valid obstacles
        # CHANGED: Added an upper range constraint (e.g., 4.5m) because iPhone LiDAR gets noisy at extreme distances
        valid_obstacle_mask = (depth > 0.15) & (depth < 4.5) & (height_grid >= ROBOT_CONFIG.CLEARANCE_HEIGHT)

        # 5. Create a filtered version of depth matrix
        # CHANGED: Replace ground/noise with NaN instead of np.inf. 
        # This allows us to use NumPy's built-in nanmedian function.
        filtered_depths = np.where(valid_obstacle_mask, depth, np.nan)

        # 6. Find the MEDIAN distance per column across all rows (Ignores NaNs)
        # Wrap in errstate to suppress warnings if a column is completely clear (all NaN)
        with np.errstate(all_nan='ignore'):
            collapsed_1d = np.nanmedian(filtered_depths, axis=0)

        # 7. Replace entirely clear columns (which result in NaN from nanmedian) with your max range (3.0m)
        collapsed_1d = np.nan_to_num(collapsed_1d, nan=3.0)

        # 8. 1D Horizontal Smoothing (3-degree moving average)
        # Drops pixel-to-pixel jitter between adjacent columns
        kernel = np.ones(3) / 3.0
        smoothed_1d = np.convolve(collapsed_1d, kernel, mode='same')

        # 9. Vectorized Obstacle Erosion (The Corner-Clipping Fix)
        # We manually tune this buffer. Since 1 column = 1 degree, a buffer of 12 
        # means we expand obstacles by 12 degrees to the left and right.
        buffer = 12
        window_width = (2 * buffer) + 1

        # Pad the boundaries using edge values so the sliding window trick doesn't break
        padded = np.pad(smoothed_1d, buffer, mode='edge')

        # Create a sliding window view over the array using NumPy stride mechanics
        shape = (smoothed_1d.size, window_width)
        strides = (padded.strides[0], padded.strides[0])
        windows = np.lib.stride_tricks.as_strided(padded, shape=shape, strides=strides)

        # Pull the minimum of the local window. This forces the obstacle profile
        # to expand horizontally, shrinking your gaps safely in software.
        min_depth_per_column = np.min(windows, axis=1)

        return min_depth_per_column



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
           col_angle = (col / ROBOT_CONFIG.GRID_COLS - 0.5) * ROBOT_CONFIG.FOV_RAD
           column_depths[col] = self.simulate_lidar_column(robot_state, col_angle)
        
           if column_depths[col] == np.inf:
               continue
           else:
               self.ray_points[col] = (column_depths[col] * math.cos(col_angle), column_depths[col] * math.sin(col_angle))
    
        # 1. Handle near-field clipping ONLY first (Keep open sky as np.inf!)
        raw_simulated_depths = np.where(column_depths < 0.15, 0.15, column_depths)

        # 2. Apply 1D Horizontal Smoothing
        kernel = np.ones(3) / 3.0
        smoothed_1d = np.convolve(raw_simulated_depths, kernel, mode='same')

        # 3. Apply Vectorized Obstacle Erosion while open space is still inf
        buffer = 10
        window_width = (2 * buffer) + 1
        padded = np.pad(smoothed_1d, buffer, mode='edge')

        shape = (smoothed_1d.size, window_width)
        strides = (padded.strides[0], padded.strides[0])
        windows = np.lib.stride_tricks.as_strided(padded, shape=shape, strides=strides)

        # Open space (inf) will lose to obstacles correctly, but obstacles won't pollute open columns past 12 cols
        simulated_min_depth_per_column = np.min(windows, axis=1)
    
        # 4. CRITICAL: Now turn remaining open spaces/inf into your maximum range threshold
        simulated_min_depth_per_column = np.where(
            simulated_min_depth_per_column > ROBOT_CONFIG.OBSTACLE_DETECTED_THRESHOLD, 
            3.0, 
            simulated_min_depth_per_column
        )
    
        self.convert_rays_to_global(robot_state)
        return simulated_min_depth_per_column

    def convert_rays_to_global(self, robot_state: RobotState):
        for i, ray in enumerate(self.ray_points):
            if ray[0] is None: continue
            self.ray_points[i] = (
                robot_state.x + ray[0] * math.cos(robot_state.yaw) - ray[1] * math.sin(robot_state.yaw),
                robot_state.y + ray[0] * math.sin(robot_state.yaw) + ray[1] * math.cos(robot_state.yaw)
            )
            
            
        
