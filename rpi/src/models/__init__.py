import json
from pathlib import Path

from .Config import RobotConfig, EMBEDDED_CONFIG_KEYS

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

from .Mode import Mode
from .Command import *
from .SensorData import *
from .PathFollowing import *
from .StateEstimation import *
from .PathFollowing import *
from .Communication import *
from .Obstacles import *
from .Manual import *
from .Bus import *
from .LoopMonitoring import LoopMonitoring
from .ConfigManager import ConfigManager
from .MetaMode import MetaMode
from .NavigationMode import NavigationMode

from .StateManager import StateManager
from .Robot import Robot
