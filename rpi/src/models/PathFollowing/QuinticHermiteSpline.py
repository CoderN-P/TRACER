import numpy as np
from typing import List
from .. import ROBOT_CONFIG
from .TrajectoryState import TrajectoryState


class QuinticHermiteSpline:
    def __init__(self, start: tuple, end: tuple, start_velocity: tuple, end_velocity: tuple, start_acceleration: tuple, end_acceleration: tuple):
        self.start = start
        self.end = end
        self.start_velocity = start_velocity
        self.end_velocity = end_velocity
        self.start_acceleration = start_acceleration
        self.end_acceleration = end_acceleration

        self.arc_length_lut = [0.0] * (ROBOT_CONFIG.SPLINE_SAMPLES + 1)
        self.curvature_lut = [0.0] * (ROBOT_CONFIG.SPLINE_SAMPLES + 1)
        self.velocity_profile = [0.0] * (ROBOT_CONFIG.SPLINE_SAMPLES + 1)
        self.time_lut = [0.0] * (ROBOT_CONFIG.SPLINE_SAMPLES + 1)
        
        
    def evaluate(self, t):
        # Hermite basis functions
        h05 = 1 - 10*t**3 + 15*t**4 - 6*t**5
        h15 = t -6*t**3 + 8*t**4 - 3*t**5
        h25 = 0.5*t**2 - 1.5*t**3 + 1.5*t**4 - 0.5*t**5
        h35 = 0.5*t**3 - t**4 + 0.5*t**5
        h45 = -4*t**3 + 7*t**4 -3*t**5
        h55 = 10*t**3 - 15*t**4 + 6*t**5
        
        x = (
            h05*self.start[0] +
            h15*self.start_velocity[0] +
            h25*self.start_acceleration[0] +
            h35*self.end_acceleration[0] +
            h45*self.end_velocity[0] +
            h55*self.end[0]
        )
        
        y = (
            h05*self.start[1] +
            h15*self.start_velocity[1] +
            h25*self.start_acceleration[1] +
            h35*self.end_acceleration[1] +
            h45*self.end_velocity[1] +
            h55*self.end[1]
        )
        
        return x, y,
    
    def evaluate_derivative(self, t):
        h05_prime = -30*t**2 + 60*t**3 - 30*t**4
        h15_prime = 1 - 18*t**2 + 32*t**3 - 15*t**4
        h25_prime = t - 4.5*t**2 + 6*t**3 - 2.5*t**4
        h35_prime = 1.5*t**2 - 4*t**3 + 2.5*t**4
        h45_prime = -12*t**2 + 28*t**3 - 15*t**4
        h55_prime = 30*t**2 - 60*t**3 + 30*t**4
        
        x_prime = (
            h05_prime*self.start[0] +
            h15_prime*self.start_velocity[0] +
            h25_prime*self.start_acceleration[0] +
            h35_prime*self.end_acceleration[0] +
            h45_prime*self.end_velocity[0] +
            h55_prime*self.end[0]
        )
        
        y_prime = (
            h05_prime*self.start[1] +
            h15_prime*self.start_velocity[1] +
            h25_prime*self.start_acceleration[1] +
            h35_prime*self.end_acceleration[1] +
            h45_prime*self.end_velocity[1] +
            h55_prime*self.end[1]
        )
        
        return x_prime, y_prime,
    
    def evaluate_second_derivative(self, t):
        h05_double_prime = -60*t + 180*t**2 - 120*t**3
        h15_double_prime = -36*t + 96*t**2 - 60*t**3
        h25_double_prime = 1 - 9*t + 18*t**2 - 10*t**3
        h35_double_prime = 3*t - 12*t**2 + 10*t**3
        h45_double_prime = -24*t + 84*t**2 - 60*t**3
        h55_double_prime = 60*t - 180*t**2 + 120*t**3
        
        x_double_prime = (
            h05_double_prime*self.start[0] +
            h15_double_prime*self.start_velocity[0] +
            h25_double_prime*self.start_acceleration[0] +
            h35_double_prime*self.end_acceleration[0] +
            h45_double_prime*self.end_velocity[0] +
            h55_double_prime*self.end[0]
        )
        
        y_double_prime = (
            h05_double_prime*self.start[1] +
            h15_double_prime*self.start_velocity[1] +
            h25_double_prime*self.start_acceleration[1] +
            h35_double_prime*self.end_acceleration[1] +
            h45_double_prime*self.end_velocity[1] +
            h55_double_prime*self.end[1]
        )
        
        return x_double_prime, y_double_prime,
    
    def build_arc_length(self):
        prev = self.evaluate(0)
        
        for i in range(1, ROBOT_CONFIG.SPLINE_SAMPLES + 1):
            t = i / ROBOT_CONFIG.SPLINE_SAMPLES
            current = self.evaluate(t)
            self.arc_length_lut[i] = self.arc_length_lut[i-1] + np.hypot(current[0] - prev[0], current[1] - prev[1])
            prev = current
            
    def build_curvature(self): 
        for i in range(0, ROBOT_CONFIG.SPLINE_SAMPLES + 1):
            t = i / ROBOT_CONFIG.SPLINE_SAMPLES
            x_prime, y_prime = self.evaluate_derivative(t)
            x_double_prime, y_double_prime = self.evaluate_second_derivative(t)
            curvature = (x_prime * y_double_prime - y_prime * x_double_prime) / ((x_prime**2 + y_prime**2)**1.5)
            self.curvature_lut[i] = curvature

    @staticmethod
    def calculate_max_velocity(curvature):
        eps = 1e-6
    
        if abs(curvature) < eps:
            return ROBOT_CONFIG.MAX_LINEAR_VEL_POS
        else:
            # Lateral accel constraint
            v_lateral = np.sqrt(ROBOT_CONFIG.MAX_LATERAL_ACCEL / abs(curvature))
    
            # Wheel speed constraint: v + |omega| * wheelbase/2 <= v_max_wheel
            # omega = v * curvature, so: v + |v * curvature| * wheelbase/2 <= v_max_wheel
            # v * (1 + |curvature| * wheelbase/2) <= v_max_wheel
            v_wheel = ROBOT_CONFIG.MAX_LINEAR_VEL_POS / (1 + abs(curvature) * ROBOT_CONFIG.WHEEL_BASE / 2)
    
            return min(v_lateral, v_wheel, ROBOT_CONFIG.MAX_LINEAR_VEL_POS)
            
    def build_velocity_profile(self, start_velocity=0, end_velocity=None):
        self.velocity_profile[0] = start_velocity
        
        for i in range(1, ROBOT_CONFIG.SPLINE_SAMPLES + 1):
            curvature = self.curvature_lut[i]
            max_vel = self.calculate_max_velocity(curvature)
            ds = self.arc_length_lut[i] - self.arc_length_lut[i-1]
            v_allowed = np.sqrt(self.velocity_profile[i-1]**2 + 2*ROBOT_CONFIG.MAX_LONG_ACCEL*ds)
            self.velocity_profile[i] = min(max_vel, v_allowed)
            
        if end_velocity is not None:
            self.velocity_profile[-1] = end_velocity
        
        for i in range(ROBOT_CONFIG.SPLINE_SAMPLES - 1, -1, -1):
            ds = self.arc_length_lut[i+1] - self.arc_length_lut[i]
            v_allowed = np.sqrt(self.velocity_profile[i+1]**2 + 2*ROBOT_CONFIG.MAX_LONG_ACCEL*ds)
            self.velocity_profile[i] = min(self.velocity_profile[i], v_allowed)
            
    def build_time_lut(self):
        for i in range(1, ROBOT_CONFIG.SPLINE_SAMPLES + 1):
            ds = self.arc_length_lut[i] - self.arc_length_lut[i-1]
            avg_vel = (self.velocity_profile[i] + self.velocity_profile[i-1]) / 2 # Trapezoidal integration
            avg_vel = max(avg_vel, 1e-6)  # Avoid division by zero
            dt = ds / avg_vel if avg_vel > 0 else 0
            self.time_lut[i] = self.time_lut[i-1] + dt
            
    def build_trajectory(self, start_velocity, end_velocity, start_timestamp) -> List[TrajectoryState]:
        self.build_arc_length()
        self.build_curvature()
        self.build_velocity_profile(start_velocity, end_velocity)
        self.build_time_lut()
        
        total_time = self.time_lut[-1]
        num_points = int(np.ceil(total_time / ROBOT_CONFIG.TRAJECTORY_DT))
        
        
        i = 0
        j = 0

        trajectory = []
        
        for k in range(0, num_points):
            t = k * ROBOT_CONFIG.TRAJECTORY_DT
            
            # Find the index with the closest time in the LUT
            while i < ROBOT_CONFIG.SPLINE_SAMPLES - 2 and self.time_lut[i] < t:
                i += 1
            
            dt = max(self.time_lut[i] - self.time_lut[i-1], 1e-6)
            
            alpha = (t - self.time_lut[i]) / dt
            s_k = self.arc_length_lut[i] + alpha * (self.arc_length_lut[i+1] - self.arc_length_lut[i])
            curvature_k = self.curvature_lut[i] + alpha * (self.curvature_lut[i+1] - self.curvature_lut[i])
            velocity_k = self.velocity_profile[i] + alpha * (self.velocity_profile[i+1] - self.velocity_profile[i])
            
            while j < ROBOT_CONFIG.SPLINE_SAMPLES - 2 and self.arc_length_lut[j] < s_k:
                j += 1
                
            ds = max((self.arc_length_lut[j+1] - self.arc_length_lut[j]), 1e-6)  # Avoid division by zero
            alpha_s = (s_k - self.arc_length_lut[j]) / ds
            u_k = (j + alpha_s) / ROBOT_CONFIG.SPLINE_SAMPLES
            
            position = self.evaluate(u_k)
            heading = np.arctan2(self.evaluate_derivative(u_k)[1], self.evaluate_derivative(u_k)[0])
            omega = curvature_k * velocity_k
            
            trajectory.append(TrajectoryState(
                x=position[0],
                y=position[1],
                theta=heading,
                v=velocity_k,
                omega=omega,
                t=t+start_timestamp
            ))
        
        return trajectory
            
            
        
        
            
        
    
            
