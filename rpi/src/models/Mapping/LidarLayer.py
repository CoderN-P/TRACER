import asyncio
import logging
import numpy as np
import time
from .OccupancyGrid import OccupancyGrid
from ..SensorData import PointCloud
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

    def update(self, point_cloud: PointCloud, pose):
        origin = (
            pose[0] + ROBOT_CONFIG.LIDAR_OFFSET_X*np.cos(pose[2])
            - ROBOT_CONFIG.LIDAR_OFFSET_Y*np.sin(pose[2]),

            pose[1] + ROBOT_CONFIG.LIDAR_OFFSET_X*np.sin(pose[2])
            + ROBOT_CONFIG.LIDAR_OFFSET_Y*np.cos(pose[2])
        )
        
        endpoints = [[point.x, point.y] for point in point_cloud.points]
        rays = self.raycast(origin, endpoints)

        for ray in rays:
            # Mark free space.
            for cell in ray[:-1]:
                x, y = cell
                if x >= self.grid_width or y >= self.grid_height:
                     self._logger.warning(ray)
                self.grid[y, x] = np.clip(self.grid[y, x] + self.FREE_UPDATE, self.CELL_MIN, self.CELL_MAX)
                self.last_seen[y, x] = point_cloud.timestamp
            x, y = ray[-1]
            if x >= self.grid_width or y >= self.grid_height:
                self._logger.warning(ray)
            # Mark occupied endpoint.
            self.grid[y, x] = np.clip(self.grid[y, x] + self.OCCUPIED_UPDATE, self.CELL_MIN, self.CELL_MAX)
            self.last_seen[y, x] = point_cloud.timestamp
                
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
                (self.grid[ys, xs] / self.CELL_MAX * 255).astype(np.uint8)
            )
        )

        data = [list(map(float, list(self.cell_to_world(cell[0], cell[1])))) + [int(cell[2])] for cell in cells] # array of x, y, intensity

        return data
