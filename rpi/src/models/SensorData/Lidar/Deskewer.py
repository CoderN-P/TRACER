import numpy as np
from . import LidarScan, Point, PointCloud, LidarPoint
from ... import ROBOT_CONFIG

class Deskewer:
    def __init__(self, state_estimator):
        self.state_estimator = state_estimator
        self.latest_snapshot_index = 0
        
    def deskew(self, scan: LidarScan):
        deskewed_points = []
        for point in scan.points:
            deskewed_point = self.deskew_point(point)
            if not point: return None
            deskewed_points.append(deskewed_point)
            
        if any([not point for point in deskewed_points]):
            return None 
            
        self.latest_snapshot_index = 0
        
        # Returns point cloud and associated robot pose
        return PointCloud(
            timestamp=scan.end_time_ns,
            points=deskewed_points
        )
    
    def deskew_point(self, point: LidarPoint):
        data = self.state_estimator.snapshot_history.interpolate_pose(point.timestamp_ns, self.latest_snapshot_index)
        if not data: return None
        
        state, idx = data
        # 1. Convert local polar point to local Cartesian (LiDAR sensor frame)
        
        self.latest_snapshot_index = idx
        
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
            [np.cos(state[2]), -np.sin(state[2]), state[0]],
            [np.sin(state[2]),  np.cos(state[2]), state[1]],
            [0.0,                  0.0,                 1.0]
        ])
    
        # 4. Chain the transformations together
        p_robot = T_lidar_to_robot @ p_lidar
        p_global = T_robot_to_global @ p_robot

        pose_origin = (
            state[0] + ROBOT_CONFIG.LIDAR_OFFSET_X*np.cos(state[2])
            - ROBOT_CONFIG.LIDAR_OFFSET_Y*np.sin(state[2]),

            state[1] + ROBOT_CONFIG.LIDAR_OFFSET_X*np.sin(state[2])
            + ROBOT_CONFIG.LIDAR_OFFSET_Y*np.cos(state[2])
        )

        return Point(
            x=p_global[0],
            y=p_global[1],
            origin_x=pose_origin[0],
            origin_y=pose_origin[1],
            quality=point.quality
        )
