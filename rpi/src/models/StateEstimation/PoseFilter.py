import numpy as np
from .. import ROBOT_CONFIG

class PoseFilter:
    def __init__(self, p: np.ndarray | None = None):
        self.Q = np.array([
            [ROBOT_CONFIG.Q_X, 0],
            [0, ROBOT_CONFIG.Q_Y],
        ])
        
        self.state = np.array([0.0, 0.0])  # [x, y]
        self.process_jacobian = np.eye(2)
        
        if p:
            self._P = p
        else:
            self._P = np.eye(2) * ROBOT_CONFIG.P_POSITION

    @property
    def P(self):
        return self._P
    
    @P.setter
    def P(self, value):
        if not isinstance(value, np.ndarray):
            self._P = np.array(value)
        else:
            self._P = value
            
    def reset(self):
        self.state = np.array([0.0, 0.0])
        
    def predict_covariance(self):
        return self.P + self.Q # process_jacobian is identity so it doesn't change P in this simple model
    
    def predict(self, delta_x, delta_y):
        self.state[0] += delta_x
        self.state[1] += delta_y
    
    def update(self, glob_x, glob_y, predicted_state, P_pred):
        y = np.array([glob_x - predicted_state[0], glob_y - predicted_state[1]])
        S = P_pred + ROBOT_CONFIG.R_POSITION * np.eye(2) # Measurement noise covariance
        K = P_pred @ np.linalg.inv(S) # Kalman gain
        
        self.state = predicted_state + K @ y
        self.P = (np.eye(2) - K) @ P_pred
    
    def step(self, delta_x, delta_y, lidar_data):
        self.predict(delta_x, delta_y)
        
        if lidar_data is not None:
            P_pred = self.predict_covariance()
            self.update(lidar_data.camera.x, lidar_data.camera.y, self.state, P_pred)
        
        return self.state
