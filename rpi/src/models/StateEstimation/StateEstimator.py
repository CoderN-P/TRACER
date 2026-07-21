import math
import asyncio
import time
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
        self.state_lock = asyncio.Lock()
        
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
        
    async def on_state_change(self, event: StateChange):
        if event.new_state == Mode.STOPPED or event.prev_state == Mode.STOPPED:
            await self.reset()

    
    def initialize(self, sensor_data: SensorData):
        self.initial_mag_heading = math.radians(sensor_data.magnetometer.heading)
        
    async def reset(self):
        async with self.state_lock:
            self._reset_unlocked()

    def _reset_unlocked(self):
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

    async def get_state_snapshot(self):
        async with self.state_lock:
            return self.state.model_copy()

    async def interpolate_pose(self, timestamp, index=0):
        async with self.state_lock:
            return self.snapshot_history.interpolate_pose(timestamp, index)

    async def apply_lidar_pose_correction(self, best_pose):
        async with self.state_lock:
            self.pose_filter.state[0] = best_pose[0]
            self.pose_filter.state[1] = best_pose[1]
            self.heading_filter.state[0] = best_pose[2]
            self.state.x = best_pose[0]
            self.state.y = best_pose[1]
            self.state.yaw = best_pose[2]

    # Python logic to find how many packets were missed
    @staticmethod
    def calculate_missed_packets(current_seq, last_seq):
        # This handles the rollover (255 -> 0)
        diff = (current_seq - last_seq) & 0xFF
        return diff - 1 # If diff is 1, 0 packets were missed
    
    @staticmethod
    def calculate_dt(cur_raw: int, previous_raw: int):
        # Timestamps in ns
        current_time = cur_raw / 1_000_000_000.0 
        previous_time = previous_raw / 1_000_000_000.0
        
        return current_time - previous_time

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


    async def update(self, sensor_data: SensorData, previous_sensor_data: SensorData):
        async with self.state_lock:
            return self._update_unlocked(sensor_data, previous_sensor_data)

    def _update_unlocked(self, sensor_data: SensorData, previous_sensor_data: SensorData):
        # Previous sensor data is needed to determine dt
        if not previous_sensor_data: return
        
        if len(self.snapshot_history.history) == 0:
            self.snapshot_history.add(EKFSnapshot(
                timestamp=sensor_data.timestamp,
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
            timestamp=sensor_data.timestamp,
            robot_state=self.state.model_copy(),
            sensor_data=sensor_data.model_copy(),
            pose_covariance=self.pose_filter.P,
            heading_covariance=self.heading_filter.P,
            gyro_bias=self.heading_filter.state[1],
            theta_encoders=self.theta_encoders
        ))
        
        return
        
    async def correct(self, timestamp, measurement):
        raise NotImplementedError("Historical EKF correction needs to be updated for locked async state access.")



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

        
