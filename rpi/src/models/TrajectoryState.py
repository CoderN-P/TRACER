from dataclasses import dataclass


@dataclass
class TrajectoryState:
    x: float        # desired x position
    y: float        # desired y position
    theta: float    # desired heading
    v: float        # desired linear velocity
    omega: float    # desired angular velocity
    t: float        # timestamp