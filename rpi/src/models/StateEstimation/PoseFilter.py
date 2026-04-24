import numpy as np
from .. import ROBOT_CONFIG

class PoseFilter:
    def __init__(self):
        self.Q = np.array([
            [ROBOT_CONFIG.Q_X, 0],
            [0, ROBOT_CONFIG.Q_Y],
        ])
        
        self.state = np.array([0, 0, 0])  # [x, y, theta]
    
    @staticmethod 
    def get_process_jacobian(linear_vel, theta, dt):
        return np.array([
            [1, 0, -linear_vel*np.sin(theta)*dt],
            [0, 1,  linear_vel*np.cos(theta)*dt],
            [0, 0, 1]
        ])
    
    def predict_covariance(self, linear_vel, theta, dt, P):
        F = self.get_process_jacobian(linear_vel, theta, dt)
        return F @ P @ F.T + self.Q
    
    def predict(self, linear_vel, theta, dt):
        x_pred = self.state[0] + linear_vel * np.cos(theta) * dt
        y_pred = self.state[1] + linear_vel * np.sin(theta) * dt
        theta_pred = (theta + np.pi) % (2 * np.pi) - np.pi
        return np.array([x_pred, y_pred, theta_pred])
    
    
    def update(self):
        # TODO: Implement this with LIDAR data for measurement.
        pass 