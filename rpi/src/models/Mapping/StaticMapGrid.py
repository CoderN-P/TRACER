import numpy as np
from pathlib import Path
import logging
from . import MAP_SAVE_DIR
from .OccupancyGrid import OccupancyGrid
from ..SensorData import PointCloud
from .. import ROBOT_CONFIG

class StaticMapGrid(OccupancyGrid):
    def __init__(self):
        super().__init__(ROBOT_CONFIG.MAX_WORLD_WIDTH, ROBOT_CONFIG.MAX_WORLD_HEIGHT, ROBOT_CONFIG.GRID_RES)
        self._logger = logging.getLogger("Robot.WorldModel.StaticMap")
                
    def load(self, name):
        try: 
            grid = np.load(MAP_SAVE_DIR / name / f"static_grid.npy")
            self.grid = grid
            return True
        except FileNotFoundError:
            self._logger.error("Map not found")
            return False

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
            for cell in ray[:-1]:
                self.decrease_occupancy(cell)
            
            self.increase_occupancy(ray[-1])
            
    def probability_at_cell(self, cell_x, cell_y):
        log_prob_cost = super().cost_at_cell(cell_x, cell_y)
        probability = 1 / (1 + np.exp(-log_prob_cost))
        return probability
    
    def cost_at_cell(self, cell_x, cell_y):
        probability = self.probability_at_cell(cell_x, cell_y)
        if probability > ROBOT_CONFIG.OBSTACLE_PROB_THRESHOLD:
            return np.inf

        return 0
    
    def cost_at(self, x, y):
        return self.cost_at_cell(*self.world_to_cell(x, y))

    def increase_occupancy(self, cell):
        cell_y, cell_x = cell
        if 0 <= cell_x < self.grid_width and 0 <= cell_y < self.grid_height:
            self.grid[cell_y, cell_x] = np.clip(self.grid[cell_y, cell_x] + ROBOT_CONFIG.LOG_ODDS_OCC, -5, 5)
            
    def decrease_occupancy(self, cell):
        cell_y, cell_x = cell
        if 0 <= cell_x < self.grid_width and 0 <= cell_y < self.grid_height:
            self.grid[cell_y, cell_x] = np.clip(self.grid[cell_y, cell_x] + ROBOT_CONFIG.LOG_ODDS_FREE, -5, 5)
            
    def save_map(self, name):
        np.save(MAP_SAVE_DIR / name / f"static_grid.npy", self.grid)

    def serialize_visualization(self):
        """
        Returns an array of all occupied cell world positions (bottom left of cell) and their intensity (0-255 grayscale)
        :return: 
        """

        probs = 1 / (1 + np.exp(-self.grid))
        mask = probs > ROBOT_CONFIG.OBSTACLE_PROB_THRESHOLD
        ys, xs = np.nonzero(mask)

        values = probs[ys, xs]
        cells = np.column_stack(
            (
                xs,
                ys,
                (values * 255).astype(np.uint8)
            )
        )
        
        data = [list(map(float, list(self.cell_to_world(cell[0], cell[1])))) + [int(cell[2])] for cell in cells] # array of x, y, intensity
        
        return data
        
