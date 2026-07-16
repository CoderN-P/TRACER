from pydantic import Field, BaseModel
import math, numpy as np
from .VirtualObstacleType import VirtualObstacleType
from ..StateEstimation import RobotState

class VirtualObstacle(BaseModel):
    obstacle_type: VirtualObstacleType = Field(default=VirtualObstacleType.CIRCLE, description="Obstacle type (rectangle/circle)")
    position: tuple[float, float] = Field(default_factory=lambda: (0, 0,), description="XY position of the center of the obstacle in meters")
    rotation: float | None = Field(default=None, description="Rotation of the virtual obstacle in radians")
    width: float | None = Field(default=None, description="Width of the rectangular obstacle in meters")
    height: float | None = Field(default=None, description="Height of the rectangular obstacle in meters")
    radius: float | None = Field(default=None, description="Radius of the circular obstacle in meters")


    def get_bounding_box(self):
        x, y = self.position

        if self.obstacle_type == VirtualObstacleType.CIRCLE:
            return (
                x - self.radius,
                y - self.radius,
                x + self.radius,
                y + self.radius,
            )

        half_w = self.width / 2
        half_h = self.height / 2

        # Conservative AABB for rotated rectangles.
        r = math.sqrt(half_w**2 + half_h**2)

        return (
            x - r,
            y - r,
            x + r,
            y + r,
        )
        
    def rasterize(self, grid):
        min_x, min_y, max_x, max_y = self.get_bounding_box()

        min_cx, min_cy = grid.world_to_cell(min_x, min_y)
        max_cx, max_cy = grid.world_to_cell(max_x, max_y)

        min_cx = max(0, min_cx)
        min_cy = max(0, min_cy)
        max_cx = min(grid.grid_width - 1, max_cx)
        max_cy = min(grid.grid_height - 1, max_cy)

        for cy in range(min_cy, max_cy + 1):
            for cx in range(min_cx, max_cx + 1):
                wx, wy = grid.cell_to_world(cx, cy)

                if self.obstacle_type == VirtualObstacleType.CIRCLE:
                    dx = wx - self.position[0]
                    dy = wy - self.position[1]

                    if dx*dx + dy*dy <= self.radius**2:
                        grid.grid[cy, cx] = np.inf

                else:
                    dx = wx - self.position[0]
                    dy = wy - self.position[1]

                    theta = -(self.rotation or 0)

                    local_x = (
                        dx * math.cos(theta)
                        - dy * math.sin(theta)
                    )
                    local_y = (
                        dx * math.sin(theta)
                        + dy * math.cos(theta)
                    )

                    if (
                        abs(local_x) <= self.width / 2
                        and abs(local_y) <= self.height / 2
                    ):
                        grid.grid[cy, cx] = np.inf

    
    
