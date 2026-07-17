import numpy as np
import logging
from . import PointCloud
from ... import ROBOT_CONFIG

class ScanMatcher:
    def __init__(self, world_model):
        self.world_model = world_model
        self.theta_range = np.pi/36 # +- 5 degrees
        # maximum translation search range in meters ( +/- xy_range )
        # tuned small for RPi5 to keep computation light; can be increased if needed
        self.xy_range = 0.2
        # number of samples for theta and xy (odd to include zero)
        self.n_theta = 11
        self.n_xy = 5
        # cache for probability grid will be refreshed each match call
        
        self.MIN_SCORE = 200
        
        self._logger = logging.getLogger("Robot.ScanMatcher")
        
    """
    Implements CSM (Correlative scan matching)
    """
    
    def match(self, point_cloud: PointCloud, pose):
        """
        Fast vectorized correlative scan matcher (CSM).

        point_cloud: PointCloud - points are given in world frame measured at `pose`.
        pose: tuple (x, y, theta) - the pose associated with the provided point cloud.

        Returns: (best_pose, best_score)
        """

        # Extract map and quick access values
        static_map = self.world_model.static_map
        
        if static_map.scans_inserted < 5:
            self._logger.info("Skipping scan matching as not enough scans have been inserted into the map.")
            return pose, 0.0
        
        grid = static_map.grid  # log-odds grid
        # Precompute probability grid once (vectorized access is much faster than calling method per point)
        prob_grid = 1.0 / (1.0 + np.exp(-grid))
        score_grid = np.where(prob_grid > ROBOT_CONFIG.LOG_ODDS_OCC, 1.0, 0.0)

        res = static_map.resolution
        origin_x = static_map.origin_x
        origin_y = static_map.origin_y

        px = np.array([p.x for p in point_cloud.points], dtype=np.float32)
        py = np.array([p.y for p in point_cloud.points], dtype=np.float32)

        # If there are no points return the input pose
        if px.size == 0:
            return pose, 0.0

        pose_x, pose_y, pose_theta = pose[0], pose[1], pose[2]

        # create candidate offsets
        theta_offsets = np.linspace(-self.theta_range, self.theta_range, self.n_theta)

        # xy offsets (symmetric) in meters
        xy_lin = np.linspace(-self.xy_range, self.xy_range, self.n_xy)

        best_score = -np.inf
        second_best = -np.inf
        best_pose = pose

        # Precompute points relative to the original pose origin for rotation about that point
        rel_x = px - pose_x
        rel_y = py - pose_y

        # Iterate over theta offsets and xy offsets; outer loops are small so Python loop is acceptable
        for dtheta in theta_offsets:
            # rotation matrix components for this dtheta
            c = np.cos(dtheta)
            s = np.sin(dtheta)

            # rotate relative points
            tx = c * rel_x - s * rel_y
            ty = s * rel_x + c * rel_y

            # now for each translation offset, translate rotated points and sample the map
            for dx in xy_lin:
                for dy in xy_lin:
                    # translate rotated points by new pose delta
                    world_x = tx + pose_x + dx
                    world_y = ty + pose_y + dy

                    # convert to cell indices (vectorized)
                    cell_x = ((world_x - origin_x) / res).astype(np.int32)
                    cell_y = ((world_y - origin_y) / res).astype(np.int32)

                    # mask valid indices
                    valid = (
                        (cell_x >= 0) & (cell_x < score_grid.shape[1]) &
                        (cell_y >= 0) & (cell_y < score_grid.shape[0])
                    )

                    if not np.any(valid):
                        # no valid points fall inside map for this hypothesis
                        score = -np.inf
                    else:
                        # sample probabilities and sum as score (higher is better)
                        sampled = score_grid[cell_y[valid], cell_x[valid]]
                        score = float(np.sum(sampled))

                    if score > best_score:
                        second_best = best_score
                        best_score = score
                        best_pose = (pose_x + dx, pose_y + dy, pose_theta + dtheta)
                    elif score > second_best:
                        second_best = score

        if best_score < MIN_SCORE:
            self._logger.warning(f"Skipping scan matching as best score ({best_score}) was worse than the minimum score ({MIN_SCORE})")
            return pose, 0
    
        if best_score < second_best * 1.05:
            self._logger.warning(f"Skipping scan matching as best score ({best_score}) was not significantly better than second best score ({second_best})")
            return pose, 0
        
        if abs(best_pose[2] - pose[2]) > 5:
            self._logger.warning(f"Skipping scan matching as the change in orientation ({(best_pose[2] - pose[2])*180/np.pi} deg) was too large.")
            return pose, 0
        
        if np.hypot(best_pose[0] - pose[0], best_pose[1] - pose[1]) > 0.1:
            self._logger.warning(f"Skipping scan matching as the change in position ({np.hypot(best_pose[0] - pose[0], best_pose[1] - pose[1])} m) was too large.")
            return pose, 0
            
        # return best pose and score
        return best_pose, best_score
        
        
        
        
