import numpy as np
from . import LidarScan, Point, PointCloud
from ... import ROBOT_CONFIG

class Deskewer:
    def __init__(self, state_estimator):
        self.state_estimator = state_estimator
        
    def deskew(self, scan: LidarScan):
        deskewed_points = []
        for point in scan.points:
            deskewed_point = self.deskew_point(point)
            deskewed_points.append(deskewed_point)
        
        # Returns point cloud and associated robot pose
        return PointCloud(
            timestamp=scan.end_time_ns,
            points=deskewed_points
        ), self.state_estimator.state_history.interpolate_pose(scna.points[-1].timestamp)
    
    def deskew_point(self, point: LidarPoint):
        state = self.state_estimator.state_history.interpolate_pose(point.timestamp)

        # 1. Convert local polar point to local Cartesian (LiDAR sensor frame)
        point_theta = np.radians(point.angle)
        
        p_lidar = np.array([
            point.distance * np.cos(point_theta),
            point.distance * np.sin(point_theta),
            1.0
        ])
    
        offset_theta = 0 # Lidar is not angled relative to robot
        # 2. Matrix: LiDAR Frame -> Robot Base Frame
        T_lidar_to_robot = np.array([
            [np.cos(offset_theta), -np.sin(offset_theta), ROBOT_CONFIG.LIDAR_OFFSET_X],
            [np.sin(offset_theta),  np.cos(offset_theta), ROBOT_CONFIG.LIDAR_OFFSET_Y],
            [0.0,                   0.0,                  1.0     ]
        ])
    
        # 3. Matrix: Robot Base Frame -> Global Frame
        T_robot_to_global = np.array([
            [np.cos(state.yaw), -np.sin(state.yaw), state.x],
            [np.sin(state.yaw),  np.cos(state.yaw), state.y],
            [0.0,                  0.0,                 1.0]
        ])
    
        # 4. Chain the transformations together
        p_robot = T_lidar_to_robot @ p_lidar
        p_global = T_robot_to_global @ p_robot

        return Point(
            x=p_global[0],
            y=p_global[1],
            quality=point.quality
        )