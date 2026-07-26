import numpy as np
import logging
from . import PointCloud
from ... import ROBOT_CONFIG

class ScanMatcher:
    def __init__(self, world_model):
        self.world_model = world_model
        self.theta_range = np.deg2rad(3) # +- 3 degrees
        # maximum translation search range in meters ( +/- xy_range )
        # tuned small for RPi5 to keep computation light; can be increased if needed
        # coarse search
        self.xy_range = 0.05
        self.n_theta = 5
        self.n_xy = 5
        
        # fine search
        self.fine_theta_range = np.deg2rad(0.5)
        self.fine_xy_range = 0.01
        self.n_theta_fine = 5
        self.n_xy_fine = 5
        
        self.MIN_SCORE = 100
        
        self._logger = logging.getLogger("Robot.ScanMatcher")
        
    """
    Implements CSM (Correlative scan matching)
    """
    
    async def match(self, point_cloud: PointCloud, pose):
        """
        Fast vectorized correlative scan matcher (CSM).

        point_cloud: PointCloud - points are given in world frame measured at `pose`.
        pose: tuple (x, y, theta) - the pose associated with the provided point cloud.

        Returns: (best_pose, best_score)
        """

        # Extract map and quick access values
        static_map = await self.world_model.get_static_map_snapshot()
        
        if static_map["scans_inserted"] < 5:
            self._logger.info("Skipping scan matching as not enough scans have been inserted into the map.")
            return pose, 0.0
        
        grid = static_map["grid"]  # log-odds grid
        # Precompute probability grid once (vectorized access is much faster than calling method per point)
        prob_grid = 1.0 / (1.0 + np.exp(-grid))
        score_grid = np.where(prob_grid > ROBOT_CONFIG.OBSTACLE_PROB_THRESHOLD, 1, 0)

        res = static_map["resolution"]
        origin_x = static_map["origin_x"]
        origin_y = static_map["origin_y"]

        # -------------------------
        # Stage 1: coarse search
        # -------------------------
        
        theta_offsets = np.linspace(
            -self.theta_range,
            self.theta_range,
            self.n_theta,
        )
        xy_offsets = np.linspace(
            -self.xy_range,
            self.xy_range,
            self.n_xy,
        )
        
        best_pose, best_score, second_best = self.search(
            theta_offsets,
            xy_offsets,
            pose,
            point_cloud,
            score_grid,
            origin_x, 
            origin_y,
            res
        )
        # -------------------------
        # Stage 2: fine search
        # -------------------------
        
        fine_theta_offsets = np.linspace(
            -self.fine_theta_range,
            self.fine_theta_range,
            self.n_theta_fine,
        )
        fine_xy_offsets = np.linspace(
            -self.fine_xy_range,
            self.fine_xy_range,
            self.n_xy_fine,
        )
        best_pose, best_score, second_best = self.search(
            fine_theta_offsets,
            fine_xy_offsets,
            best_pose,
            point_cloud,
            score_grid,
            origin_x,
            origin_y,
            res
        )
        print(f"Best: {best_score}, second_best: {second_best}")
        if best_score < self.MIN_SCORE:
            self._logger.warning(f"Skipping scan matching as best score ({best_score}) was worse than the minimum score ({self.MIN_SCORE})")
            return pose, 0
    
        if best_score < second_best * 1.01:
            return pose, 0
        
        if abs(best_pose[2] - pose[2]) > np.deg2rad(5):
            self._logger.warning(f"Skipping scan matching as the change in orientation ({(best_pose[2] - pose[2])*180/np.pi} deg) was too large.")
            return pose, 0
        
        if np.hypot(best_pose[0] - pose[0], best_pose[1] - pose[1]) > 0.1:
            self._logger.warning(f"Skipping scan matching as the change in position ({np.hypot(best_pose[0] - pose[0], best_pose[1] - pose[1])} m) was too large.")
            return pose, 0
        
        self._logger.info(f"Scan matching successful, best score: {best_score}, dx: {best_pose[0] - pose[0]}, dy: {best_pose[1] - pose[1]}, dtheta: {(best_pose[2] - pose[2])*180/np.pi} ")            
        # return best pose and score
        return best_pose, best_score

    @staticmethod
    def search(theta_offsets, xy_offsets, center_pose, point_cloud, score_grid, origin_x, origin_y, res):
        best_local_score = -np.inf
        second_local_score = -np.inf
        best_local_pose = center_pose

        px = np.array([p.x for p in point_cloud.points], dtype=np.float32)
        py = np.array([p.y for p in point_cloud.points], dtype=np.float32)

        # If there are no points return the input pose
        if px.size == 0:
            return center_pose, 0.0, -np.inf

        center_x, center_y, center_theta = center_pose[0], center_pose[1], center_pose[2]

        cos_theta = np.cos(center_theta)
        sin_theta = np.sin(center_theta)
        
        # Transform world-frame points back into the robot frame of center_pose.
        robot_x = (
                cos_theta * (px - center_x)
                + sin_theta * (py - center_y)
        )
        robot_y = (
                -sin_theta * (px - center_x)
                + cos_theta * (py - center_y)
        )
        
        for dtheta in theta_offsets:
            candidate_theta = center_theta + dtheta
        
            c = np.cos(candidate_theta)
            s = np.sin(candidate_theta)
        
            for dx in xy_offsets:
                for dy in xy_offsets:
                    candidate_x = center_x + dx
                    candidate_y = center_y + dy
        
                    # Apply the candidate pose transform to the scan.
                    world_x = c * robot_x - s * robot_y + candidate_x
                    world_y = s * robot_x + c * robot_y + candidate_y
    
                    cell_x = ((world_x - origin_x) / res).astype(np.int32)
                    cell_y = ((world_y - origin_y) / res).astype(np.int32)
    
                    valid = (
                            (cell_x >= 0)
                            & (cell_x < score_grid.shape[1])
                            & (cell_y >= 0)
                            & (cell_y < score_grid.shape[0])
                    )
    
                    if not np.any(valid):
                        score = -np.inf
                    else:
                        score = float(np.sum(score_grid[cell_y[valid], cell_x[valid]]))
    
                    if score > best_local_score:
                        second_local_score = best_local_score
                        best_local_score = score
                        best_local_pose = (
                            candidate_x,
                            candidate_y,
                            center_theta + dtheta,
                        )
                    elif score > second_local_score:
                        second_local_score = score
    
        return best_local_pose, best_local_score, second_local_score
        
        
        
        
