import numpy as np
from skimage.draw import line

class OccupancyGrid:
    def __init__(self, width, height, resolution):
        self.width = width # In meters
        self.height = height # In meters
        self.resolution = resolution # meters per cell
        
        self.grid_width = int(width / resolution)
        self.grid_height = int(height / resolution)
        
        self.grid = np.array([[0 for _ in range(self.grid_width)] for _ in range(self.grid_height)])
        
        self.origin_x = -width / 2
        self.origin_y = -height / 2
        
    def world_to_cell(self, x, y):
        
        cell_x = int((x - self.origin_x) / self.resolution)
        cell_y = int((y - self.origin_y) / self.resolution)
        return cell_x, cell_y
    
    def cell_to_world(self, cell_x, cell_y):
        """
        Returns the bottom left of the cell in world coords
        :param cell_x: 
        :param cell_y: 
        :return: 
        """
        x = cell_x * self.resolution + self.origin_x    
        y = cell_y * self.resolution + self.origin_y
        return x, y
    
    def cost_at_cell(self, cell_x, cell_y):
        if 0 <= cell_x < self.width and 0 <= cell_y < self.height:
            return self.grid[cell_y][cell_x]
        else:
            return None  # Out of bounds
        
    def cost_at(self, x, y):
        cell_x, cell_y = self.world_to_cell(x, y)
        return self.cost_at_cell(cell_x, cell_y)
        
    def clear(self):
        self.grid = [[0 for _ in range(self.width)] for _ in range(self.height)]
        
    def raycast(self, origin, endpoints):
        rays = []
        origin_cell_x, origin_cell_y = self.world_to_cell(origin[0], origin[1])
        for pt in endpoints:
            # Get y and x coordinate arrays for this single ray
            cell_x, cell_y = self.world_to_cell(pt[0], pt[1])
            rr, cc = line(origin_cell_y, origin_cell_x, cell_y, cell_x)
        
            # Stack them together into an (N, 2) array of coordinates
            ray_coords = np.column_stack((rr, cc))
            rays.append(ray_coords)
            
        return rays
