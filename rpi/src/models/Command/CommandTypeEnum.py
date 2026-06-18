from enum import Enum

class CommandType(str, Enum):
    OLED = "OLED"
    MOTOR = "MOTOR"
    SENSOR = "SENSOR"
    STOP = "STOP"
    ENABLE = "ENABLE" 
    PWM = "PWM"
    CONFIG = "CONFIG"
    TWIST = "TWIST"
    

    def __str__(self):
        return self.value

 