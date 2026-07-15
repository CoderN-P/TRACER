import logging
import numpy as np
import time
from .OccupancyGrid import OccupancyGrid
from ..SensorData import PointCloud
from ..StateEstimation import RobotState
from .. import ROBOT_CONFIG

class LidarLayer(OccupancyGrid):
    def __init__(self):
        super().__init__(ROBOT_CONFIG.MAX_WORLD_WIDTH, ROBOT_CONFIG.MAX_WORLD_HEIGHT, ROBOT_CONFIG.GRID_RES)
        self._logger = logging.getLogger("Robot.WorldModel.LidarLayer")

        self.last_decay_time: float = 0.0
        self.decay_dt = 1 / ROBOT_CONFIG.LIDAR_DECAY_FREQ
        self.last_seen = np.array([[0 for _ in range(self.grid_width)] for _ in range(self.grid_height)])
        
        self.FREE_UPDATE = -1
        self.OCCUPIED_UPDATE = 2
        self.CELL_MIN = -10
        self.CELL_MAX = 10

    def update(self, point_cloud: PointCloud, pose: RobotState):
        origin = (
            pose.x + offset_x*np.cos(pose.yaw)
            - offset_y*np.sin(pose.yaw),

            pose.y + offset_x*np.sin(pose.yaw)
            + offset_y*np.cos(pose.yaw)
        )
        
        endpoints = [[point.x, point.y] for point in point_cloud.points]
        rays = self.raycast(origin, endpoints)

        for ray in rays:
            # Mark free space.
            for cell in ray[:-1]:
                x, y = cell
                self.grid[y, x] = np.clip(self.grid[y, x] + self.FREE_UPDATE, self.CELL_MIN, self.CELL_MAX)
                self.last_seen[y, x] = point_cloud.timestamp_ns

            # Mark occupied endpoint.
            if ray:
                x, y = ray[-1]
                self.grid[y, x] = np.clip(self.grid[y, x] + self.OCCUPIED_UPDATE, self.CELL_MIN, self.CELL_MAX)
                self.last_seen[y, x] = point_cloud.timestamp_ns
                
    def decay(self):
        if not asyncio.get_event_loop().time() - self.last_decay_time >= self.decay_dt:
            return
        
        now = time.perf_counter_ns()
        mask = (now - self.last_seen) > ROBOT_CONFIG.LIDAR_TIMEOUT_NS
        self.grid[mask] = 0
        self.last_decay_time = asyncio.get_event_loop().time()
        
    def serialize_visualization(self):
        mask = self.grid > 0

        ys, xs = np.nonzero(mask)

        cells = np.column_stack(
            (
                xs,
                ys,
                (self.grid[ys, xs] / MAX_VALUE * 255).astype(np.uint8)
            )
        )

        data = [self.cell_to_world(cell[0], cell[1]) + [cell[2]] for cell in cells] # array of x, y, intensity

        return data