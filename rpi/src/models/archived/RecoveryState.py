from enum import Enum

class RecoveryState(Enum):
    TRACKING = "tracking"
    SCANNING = "scanning"
    ALIGNING = "aligning"