from enum import Enum


class ControllerState(str, Enum):
    ONE_ARCADE = "one_arcade" # One joystick arcade drive
    TWO_ARCADE = "two_arcade" # Two joystick arcade drive
    TANK = "tank" # Tank drive with two joysticks
    CAR = "car" # Car-like drive with triggers for acceleration and braking and left joystick for steering
    