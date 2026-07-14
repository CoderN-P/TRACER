from pathlib import Path
import logging
from . import EMBEDDED_CONFIG_KEYS, ROBOT_CONFIG
from .Command import ConfigCommand, Command, CommandType

CONSTANTS_SAVE_FILE = (
        Path(__file__).resolve().parents[2]
        / "calibration_files"
        / "constants"
        / "constants.json"
)

class ConfigManager:
    def __init__(self, command_manager):
        self.command_manager = command_manager
        self._logger = logging.getLogger("Robot.ConfigManager")
        
    
    async def update_embedded_config(self, data):
        config_command = ConfigCommand.model_validate(data)
        command = Command(
            ID="",
            command_type=CommandType.CONFIG,
            command=config_command,
            pause_duration=0,
            duration=0,
        )

        await self.command_manager.send_safe_command(command)
        
    async def init(self):
        self.load_persisted_constants()
        embedded_config = {attr: getattr(ROBOT_CONFIG, attr) for attr in EMBEDDED_CONFIG_KEYS.keys()}
        await self.update_embedded_config(embedded_config)
        
    @staticmethod
    def persist_constants():
        try:
            CONSTANTS_SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
            constants = asdict(ROBOT_CONFIG)
            with CONSTANTS_SAVE_FILE.open("w", encoding="utf-8") as fh:
                json.dump(constants, fh, indent=2, sort_keys=True)
            self._logger.info(f"Persisted constants to {CONSTANTS_SAVE_FILE}")
        except Exception as exc:
            self._logger.warning(f"Failed to persist constants: {exc}")
            
    @staticmethod
    def load_persisted_constants():
        if not CONSTANTS_SAVE_FILE.exists():
            return

        try:
            with CONSTANTS_SAVE_FILE.open("r", encoding="utf-8") as fh:
                saved = json.load(fh)
    
            if not isinstance(saved, dict):
                logger.warning("Ignoring malformed constants file: expected object")
                return
    
            applied = 0
            for attr, val in saved.items():
                if hasattr(ROBOT_CONFIG, attr):
                    try:
                        setattr(ROBOT_CONFIG, attr, val)
                        applied += 1
                    except AttributeError:
                        logger.warning(f"Skipped read-only constant '{attr}' from saved file")
            logger.info(f"Loaded {applied} persisted constants from {CONSTANTS_SAVE_FILE}")
        except Exception as exc:
            logger.warning(f"Failed to load persisted constants: {exc}")
            
            
    async def update_constants(self, data):
        if not isinstance(data, dict):
            self._logger.warning("Ignoring update_constants payload: expected object")
            return

        save_requested = bool(data.get("save", False))
        constants_payload = {k: v for k, v in data.items() if k != "save"}

        embedded_keys = []

        for attr, val in constants_payload.items():
            if not hasattr(ROBOT_CONFIG, attr):
                self._logger.warning(f"Ignoring unknown constant '{attr}'")
                continue
            try:
                if attr in EMBEDDED_CONFIG_KEYS.keys() and val != getattr(ROBOT_CONFIG, attr):
                    embedded_keys.append(attr)

                setattr(ROBOT_CONFIG, attr, val)

            except AttributeError:
                self._logger.warning(f"Ignoring read-only constant '{attr}'")

        # Save embedded keys that are diff than their current values

        if embedded_keys:
            await self.update_embedded_config({k: constants_payload[k] for k in embedded_keys})

        if save_requested:
            self.persist_constants()

        self._logger.info(f"Updated constants: {constants_payload} (save={save_requested})")
