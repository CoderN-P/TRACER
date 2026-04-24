from enum import Enum

class CommandType(str, Enum):
    LCD = "LCD"
    MOTOR = "MOTOR"
    LED = "LED"
    BUZZER = "BUZZER"
    SENSOR = "SENSOR"
    STOP = "STOP"
    ENABLE = "ENABLE" 
    PWM = "PWM"
    

    def __str__(self):
        return self.value

 