from typing import List
from collections import deque
import numpy as np
from . import EKFSnapshot
from .. import ROBOT_CONFIG


class StateHistory:
    def __init__(self, max_length=100):
        self.max_length = max_length
        self.history: deque[EKFSnapshot] = deque(maxlen=ROBOT_CONFIG.STATE_HISTORY_SIZE)

    def add(self, snapshot):
        self.history.append(snapshot)

    def clear(self):
        self.history.clear()
        
    def get_closest_idx(self, timestamp, index = 0):
        closest_idx = 0
        closest_error = float("inf")

        for i in range(index, len(self.history)):
            error = abs(
                self.history[i].timestamp -
                timestamp
            )

            if error < closest_error:
                closest_error = error
                closest_idx = i

        return closest_idx
    
    @staticmethod
    def interp_angle(a, b, alpha):
        diff = (b - a + np.pi) % (2*np.pi) - np.pi
        return a + alpha * diff
    
    def interpolate_pose(self, timestamp, index=0):
        if len(self.history) < 2:
            return None

        closest_idx = self.get_closest_idx(timestamp, index)

        if timestamp > self.history[closest_idx].timestamp:
            if closest_idx == len(self.history) - 1:
                state = self.history[-1].robot_state
                return (
                    state.x,
                    state.y,
                    state.yaw,
                    state.linear_velocity,
                    state.angular_velocity,
                    state.v_left,
                    state.v_right
                ), closest_idx
            prev_snapshot = self.history[closest_idx]
            next_snapshot = self.history[closest_idx + 1]
        else:
            if closest_idx == 0:
                return (
                    self.history[0].robot_state.x,
                    self.history[0].robot_state.y,
                    self.history[0].robot_state.yaw,
                    self.history[0].robot_state.linear_velocity,
                    self.history[0].robot_state.angular_velocity,
                    self.history[0].robot_state.v_left,
                    self.history[0].robot_state.v_right
                ), closest_idx
            prev_snapshot = self.history[closest_idx - 1]
            next_snapshot = self.history[closest_idx]

        t0 = prev_snapshot.timestamp
        t1 = next_snapshot.timestamp

        if t1 == t0:
            return (
                prev_snapshot.robot_state.x,
                prev_snapshot.robot_state.y,
                prev_snapshot.robot_state.yaw,
                prev_snapshot.robot_state.linear_velocity,
                prev_snapshot.robot_state.angular_velocity,
                prev_snapshot.robot_state.v_left,
                prev_snapshot.robot_state.v_right
            ), closest_idx

        alpha = (timestamp - t0) / (t1 - t0)
        
        # For theta (yaw), clamp both next and prev to be between -pi and pi to avoid wierd effects when interpolating

        interpolated_pose = (
            prev_snapshot.robot_state.x + alpha * (next_snapshot.robot_state.x - prev_snapshot.robot_state.x),
            prev_snapshot.robot_state.y + alpha * (next_snapshot.robot_state.y - prev_snapshot.robot_state.y),
            self.interp_angle(prev_snapshot.robot_state.yaw, next_snapshot.robot_state.yaw, alpha),
            prev_snapshot.robot_state.linear_velocity + alpha * (next_snapshot.robot_state.linear_velocity - prev_snapshot.robot_state.linear_velocity),
            prev_snapshot.robot_state.angular_velocity + alpha * (next_snapshot.robot_state.angular_velocity - prev_snapshot.robot_state.angular_velocity),
            prev_snapshot.robot_state.v_left + alpha * (next_snapshot.robot_state.v_left - prev_snapshot.robot_state.v_left),
            prev_snapshot.robot_state.v_right + alpha * (next_snapshot.robot_state.v_right - prev_snapshot.robot_state.v_right),
        )

        return interpolated_pose, closest_idx
