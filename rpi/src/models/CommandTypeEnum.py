from enum import Enum

class CommandType(Enum):
    LCD = "LCD"
    MOTOR = "MOTOR"
    LED = "LED"
    BUZZER = "BUZZER"
    SENSOR = "SENSOR", # GET SENSOR DATA
    STOP = "STOP"
    

    def __str__(self):
        return self.value

 