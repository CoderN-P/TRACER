from enum import Enum

class CommandType(str, Enum):
    LCD = "LCD"
    MOTOR = "MOTOR"
    LED = "LED"
    BUZZER = "BUZZER"
    SENSOR = "SENSOR"
    STOP = "STOP"
    

    def __str__(self):
        return self.value

 