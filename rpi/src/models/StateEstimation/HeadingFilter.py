import numpy as np
import math
from .. import ROBOT_CONFIG


class HeadingFilter:
    def __init__(self):
        self.P = np.array(
            [[ROBOT_CONFIG.P_THETA, ROBOT_CONFIG.P_THETA_BIAS],
             [ROBOT_CONFIG.P_THETA_BIAS, ROBOT_CONFIG.P_GYRO_BIAS]]
        )
        # Process noise covariance matrix Q, representing the uncertainty in the process model
        self.Q = np.array( 
            [[ROBOT_CONFIG.Q_THETA_1, 0], 
             [0, ROBOT_CONFIG.Q_BIAS]]
        )
        
        self.state = np.array([0, 0])
        
    def reset(self):
        self.state = np.array([0, 0])
        
    @staticmethod 
    def get_process_jacobian(dt):
        return np.array(
            [[1, -dt],   # d(theta_pred)/d(theta) = 1, d(theta_pred)/d(gyro_bias) = -dt
             [0, 1]]     # d(gyro_bias_pred)/d(theta) = 0, d(gyro_bias_pred)/d(gyro_bias) = 1]
        )
    
    def predict_covariance(self, dt):
        F = self.get_process_jacobian(dt)
        return F @ self.P @ F.T + self.Q
        
    def predict(self, gyro_z, dt):
        theta_pred = self.state[0] + (gyro_z - self.state[1]) * dt
        bias_pred = self.state[1]
        
        # Normalize theta_pred to be within [-pi, pi]
        theta_pred = (theta_pred + math.pi) % (2 * math.pi) - math.pi
        return np.array([theta_pred, bias_pred])
        
    def update(self, theta_meas, predicted_state, P_pred, mag_heading=None):
        y = (theta_meas - predicted_state[0] + math.pi) % (2*math.pi) - math.pi  # Measurement residual
        S = P_pred[0][0]  + ROBOT_CONFIG.R_THETA_ENCODER
        K = P_pred[:, 0] / S
        mid_state = predicted_state + K * y
        IKH = np.array(
            [[1 - K[0], 0], 
             [-K[1], 1]]        
        ) 
        P_mid = IKH @ P_pred @ IKH.T + np.outer(K, K) * ROBOT_CONFIG.R_THETA_ENCODER
        
        if mag_heading is not None:
            y_mag = (mag_heading - mid_state[0] + math.pi) % (2*math.pi) - math.pi
            S_mag = P_mid[0][0] + ROBOT_CONFIG.R_THETA_MAGNETOMETER
            K_mag = P_mid[:, 0] / S_mag
            self.state = mid_state + K_mag * y_mag
            IKH_mag = np.array(
                [[1 - K_mag[0], 0],
                 [-K_mag[1], 1]]
            )
            self.P = IKH_mag @ P_mid @ IKH_mag.T + np.outer(K_mag, K_mag) * ROBOT_CONFIG.R_THETA_ENCODER
        else:
            self.state = mid_state
            self.P = P_mid
        
    def step(self, theta_meas, gyro_z, dt, mag_heading=None):
        predicted_state = self.predict(gyro_z, dt)
        P_pred = self.predict_covariance(dt)
        self.update(theta_meas, predicted_state, P_pred, mag_heading)
        return self.state[0]
    
    