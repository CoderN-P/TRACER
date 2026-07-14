import math
import numpy as np
import time
from collections import deque
import logging
from ..PathFollowing.utils import get_ekf_track_width
from . import RobotState, HeadingFilter, PoseFilter, EKFSnapshot, StateHistory
from ..Bus import StateChange
from .. import SensorData, ROBOT_CONFIG, Mode


class StateEstimator:
    def __init__(self, bus):
        self.state: RobotState = RobotState(
            x=0.0,
            y=0.0,
            yaw=0.0,
            pitch=0.0,
            roll=0.0,
            linear_velocity=0.0,
            angular_velocity=0.0,
            v_left=0.0,
            v_right=0.0
        )
        
        self.snapshot_history = StateHistory()
        # Pre state estimations
        self.initial_mag_heading = None
        self.theta_encoders = 0.0 # Cumulative heading change from encoders, in radians
        self._logger = logging.getLogger("Robot.StateEstimator")
        self.heading_filter = HeadingFilter()
        self.pose_filter = PoseFilter()
        
        self.bus = bus
        
        self.bus.subscribe(
            StateChange,
            self.on_state_change
        )
        
    def on_state_change(self, event: StateChange):
        if event.new_state == Mode.STOPPED or event.prev_state == Mode.STOPPED:
            self.reset()

    
    def initialize(self, sensor_data: SensorData):
        self.initial_mag_heading = math.radians(sensor_data.magnetometer.heading)
        
    def reset(self):
        self.state = RobotState(
            x=0.0,
            y=0.0,
            yaw=0.0,
            pitch=0.0, # Not used
            roll=0.0,  # Not used
            linear_velocity=0.0,
            angular_velocity=0.0,
            v_left=0.0,
            v_right=0.0
        )
        self.theta_encoders = 0.0
        self.initial_mag_heading = None
        self.heading_filter.reset()
        self.pose_filter.reset()
        self.snapshot_history.clear()

    # Python logic to find how many packets were missed
    @staticmethod
    def calculate_missed_packets(current_seq, last_seq):
        # This handles the rollover (255 -> 0)
        diff = (current_seq - last_seq) & 0xFF
        return diff - 1 # If diff is 1, 0 packets were missed
    
    @staticmethod
    def calculate_dt(cur_raw: float, previous_raw: float):
        current_time = cur_raw / 1_000_000.0
        previous_time = previous_raw / 1_000_000.0
        
        if current_time < previous_time:
            dt = (current_time + (4294.967295 - previous_time))  # Handle rollover (4.294967295 seconds for 32-bit microsecond timer)
        else:
            dt = current_time - previous_time
            
        return dt

    @staticmethod
    def estimate_linear_velocity(v_left, v_right):
        linear_velocity = (v_left + v_right) / 2
        return linear_velocity
    
    @staticmethod
    def get_wheel_velocities(left_ticks, right_ticks, dt):
        delta_left = left_ticks * (
            ROBOT_CONFIG.METERS_PER_TICK_LEFT_POS
            if left_ticks >= 0
            else ROBOT_CONFIG.METERS_PER_TICK_LEFT_NEG
        )
        delta_right = right_ticks * (
            ROBOT_CONFIG.METERS_PER_TICK_RIGHT_POS
            if right_ticks >= 0
            else ROBOT_CONFIG.METERS_PER_TICK_RIGHT_NEG
        )
        
        return delta_left / dt, delta_right / dt

    @staticmethod
    def _wrap_to_pi(angle: float) -> float:
        return (angle + math.pi) % (2 * math.pi) - math.pi

    @staticmethod
    def get_position_delta(left_ticks, right_ticks, heading, prev_heading):
        # 1. Distances of each wheel
        delta_l = left_ticks * (
            ROBOT_CONFIG.METERS_PER_TICK_LEFT_POS
            if left_ticks >= 0
            else ROBOT_CONFIG.METERS_PER_TICK_LEFT_NEG
        )
        delta_r = right_ticks * (
            ROBOT_CONFIG.METERS_PER_TICK_RIGHT_POS
            if right_ticks >= 0
            else ROBOT_CONFIG.METERS_PER_TICK_RIGHT_NEG
        )
    
        # 2. Wrap-safe heading and angular delta
        d_heading = StateEstimator._wrap_to_pi(heading - prev_heading)
    
        # 3. Handle pure translation vs curvature (arc)
        if abs(d_heading) < 1e-6:
            delta_s = 0.5 * (delta_l + delta_r)
            return delta_s * math.cos(heading), delta_s * math.sin(heading)
        else:
            # Radius of curvature (R = arc_length / angle)
            radius = 0.5 * (delta_l + delta_r) / d_heading
    
            # 4. Exact arc translation delta (using chord length)
            delta_x = 2 * radius * math.sin(0.5 * d_heading)
    
            # 5. Rotate the chord vector to the field frame 
            # (Alternatively: theta_c = prev_heading + 0.5 * d_heading)
            # Using the midpoint angle as the rotation vector aligns the chord correctly with the actual arc path, especially for larger turns, and avoids underestimating the lateral movement that occurs during a turn.
            theta_c = StateEstimator._wrap_to_pi(prev_heading + 0.5 * d_heading)
            return delta_x * math.cos(theta_c), delta_x * math.sin(theta_c)


    def update(self, sensor_data: SensorData, previous_sensor_data: SensorData):
        # Previous sensor data is needed to determine dt
        if not previous_sensor_data: return
        
        if len(self.history) == 0:
            self.history.add(EKFSnapshot(
                timestamp=time.time_ns() // 1000,
                robot_state=self.state.model_copy(),
                sensor_data=previous_sensor_data.model_copy(),
                heading_covariance=self.heading_filter.P,
                pose_covariance=self.pose_filter.P,
                gyro_bias=self.heading_filter.state[1],
                theta_encoders=self.theta_encoders
            ))
            
        dt = self.calculate_dt(sensor_data.timestamp, previous_sensor_data.timestamp)
        
        if dt < 1e-6: return
        
        max_pulses = ROBOT_CONFIG.ENCODER_TICKS_PER_REV * ROBOT_CONFIG.MAX_RPM / 60.0 * dt * ROBOT_CONFIG.MAX_ENCODER_MARGIN

        delta_left_ticks = sensor_data.left_encoder
        delta_right_ticks = sensor_data.right_encoder
        
        if delta_left_ticks > max_pulses or delta_right_ticks > max_pulses:
            self._logger.warning(f"Wheel encoders reported more ticks than expected: L: {delta_left_ticks}, R: {delta_right_ticks}, Expected: {max_pulses}")
            
        v_prev = self.snapshot_history.history[-1].robot_state.linear_velocity
        omega_prev = self.snapshot_history.history[-1].robot_state.angular_velocity
        self.theta_encoders += self.heading_delta_from_encoders(delta_left_ticks, delta_right_ticks, v_prev, omega_prev)
        
        if sensor_data.magnetometer.new and sensor_data.magnetometer.is_available():
            mag_heading_rad = math.radians(sensor_data.magnetometer.heading)
            if self.initial_mag_heading is not None:
                mag_heading_rad -= self.initial_mag_heading
                mag_heading_rad = (mag_heading_rad + math.pi) % (2 * math.pi) - math.pi
            else:
                self.initial_mag_heading = math.radians(sensor_data.magnetometer.heading)
                mag_heading_rad = 0.0
        else:
            mag_heading_rad = None
            
        self.state.yaw = (self.heading_filter.step(self.theta_encoders, sensor_data.imu.gyroscope_z, dt, mag_heading_rad)) % (2 * math.pi)
    
        self.state.v_left, self.state.v_right = self.get_wheel_velocities(delta_left_ticks, delta_right_ticks, dt)
        self.state.linear_velocity = self.estimate_linear_velocity(self.state.v_left, self.state.v_right)
        self.state.angular_velocity = sensor_data.imu.gyroscope_z - self.heading_filter.state[1]

        position_delta_x, position_delta_y = self.get_position_delta(delta_left_ticks, delta_right_ticks, self.state.yaw, self.snapshot_history.history[-1].robot_state.yaw)
        
        self.state.x, self.state.y = self.pose_filter.step(position_delta_x, position_delta_y, None)

        self.snapshot_history.add(EKFSnapshot(
            timestamp=time.perf_counter_ns(),
            robot_state=self.state.model_copy(),
            sensor_data=sensor_data.model_copy(),
            pose_covariance=self.pose_filter.P,
            heading_covariance=self.heading_filter.P,
            gyro_bias=self.heading_filter.state[1],
            theta_encoders=self.theta_encoders
        ))
        
        return
        
    def correct(self, timestamp, measurement):
        closest_idx = self.snapshot_history.get_closest_idx(timestamp)
        
        if closest_idx < 1:
            return
        
        # Repeat all the steps from closest_idx to the end of history, but with the lidar update at closest_idx
        # Run once with injected lidar measurement then call update for the following snapshots
        closest = self.history[closest_idx]
        self.heading_filter.P = closest.heading_covariance
        self.heading_filter.state = np.array([closest.robot_state.yaw, closest.gyro_bias])
        self.pose_filter.P = closest.pose_covariance

        self.pose_filter.state = np.array([closest.robot_state.x, closest.robot_state.y])
        self.theta_encoders = closest.theta_encoders
        self.state = closest.robot_state

        # Clear outdated snapshots 
        removed = 0
        sensor_data_history = []
        while len(self.snapshot_history.history) > closest_idx + 1:
            removed += 1
            sensor_data_history.append(self.snapshot_history.history.pop().sensor_data)

        # update the closest snapshot with scan matching measurement
        self.pose_filter.update(lidar_data.camera.x, lidar_data.camera.y, self.pose_filter.state, self.pose_filter.P)

        # re run by calling update for the number of snapshots we removed
        for i in range(0, removed):
            if i == 0:
                self.update(sensor_data_history[removed - 1 - i], self.snapshot_history.history[-1].sensor_data)
            else:
                self.update(sensor_data_history[removed - 1 - i], sensor_data_history[removed - i])



    @staticmethod
    def heading_delta_from_encoders(left_ticks, right_ticks, v_prev, omega_prev):
        delta_left = left_ticks * (
            ROBOT_CONFIG.METERS_PER_TICK_LEFT_POS
            if left_ticks >= 0
            else ROBOT_CONFIG.METERS_PER_TICK_LEFT_NEG
        )
        delta_right = right_ticks * (
            ROBOT_CONFIG.METERS_PER_TICK_RIGHT_POS
            if right_ticks >= 0
            else ROBOT_CONFIG.METERS_PER_TICK_RIGHT_NEG
        )
        
        w_eff = get_ekf_track_width(v_prev, omega_prev)
        return (delta_right - delta_left) / w_eff

        
