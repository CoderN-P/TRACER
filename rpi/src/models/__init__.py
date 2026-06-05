import json
from pathlib import Path

from .Config import RobotConfig

CONFIG_FILE = (
	Path(__file__).resolve().parents[3]
	/ "calibration_files"
	/ "constants"
	/ "constants.json"
)


def _load_robot_config() -> RobotConfig:
	with CONFIG_FILE.open("r", encoding="utf-8") as fh:
		data = json.load(fh)

	if not isinstance(data, dict):
		raise ValueError(f"Invalid constants file format: {CONFIG_FILE}")

	return RobotConfig(**data)


ROBOT_CONFIG = _load_robot_config()  # Singleton config instance loaded from constants.json

from .Command import *
from .SensorData import *
from .PathFollowing import *
from .StateEstimation import *
from .PathFollowing import *
from .SerialManager import SerialManager
from .Command import Command
from .VirtualObstacleType import VirtualObstacleType
from .VirtualObstacle import VirtualObstacle
from .ObstacleMode import ObstacleMode
from .ObstacleState import ObstacleState
from .Gap import Gap
from .RecoveryState import RecoveryState
from .GapNavigator import GapNavigator
from .MetaMode import MetaMode
from .Mode import Mode
from .Robot import Robot
