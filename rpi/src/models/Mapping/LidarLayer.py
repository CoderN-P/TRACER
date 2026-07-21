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

    def update(self, point_cloud: PointCloud):
        rays = self.raycast(point_cloud)

        free_cells = []
        occupied_cells = []

        for ray in rays:
            if len(ray) == 0:
                continue

            if len(ray) > 1:
                free_cells.append(ray[:-1])

            occupied_cells.append(ray[-1])

        if free_cells:
            free_cells = np.concatenate(free_cells)

            self.grid[
                free_cells[:, 0],
                free_cells[:, 1]
            ] += self.FREE_UPDATE

            self.last_seen[
                free_cells[:, 0],
                free_cells[:, 1]
            ] = point_cloud.timestamp

        if occupied_cells:
            occupied_cells = np.array(occupied_cells)

            self.grid[
                occupied_cells[:, 0],
                occupied_cells[:, 1]
            ] += self.OCCUPIED_UPDATE

            self.last_seen[
                occupied_cells[:, 0],
                occupied_cells[:, 1]
            ] = point_cloud.timestamp

        np.clip(self.grid, self.CELL_MIN, self.CELL_MAX, out=self.grid)
                
    def decay(self):
        if not time.monotonic() - self.last_decay_time >= self.decay_dt:
            return
        
        now = time.perf_counter_ns()
        mask = (now - self.last_seen) > ROBOT_CONFIG.LIDAR_TIMEOUT_NS
        self.grid[mask] = 0
        self.last_decay_time = time.monotonic()
        
    def serialize_visualization(self):
        mask = self.grid > 0

        ys, xs = np.nonzero(mask)

        if len(xs) == 0:
            return []

        values = (
            self.grid[ys, xs] / self.CELL_MAX * 255
        ).astype(np.uint8)

        world_x = (xs * self.resolution) + self.origin_x
        world_y = (ys * self.resolution) + self.origin_y

        data = np.column_stack(
            (
                world_x.astype(np.float32),
                world_y.astype(np.float32),
                values
            )
        )

        return data.tolist()
