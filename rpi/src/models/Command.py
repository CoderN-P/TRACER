from pydantic import BaseModel, Field
import uuid
from .LCDCommand import LCDCommand
from .MotorCommand import MotorCommand
from .CommandTypeEnum import CommandType



class Command(BaseModel):
    """
    Represents a command to be executed by the robot.
    """
    ID: str = Field(..., description="Unique identifier for the command")
    command_type: CommandType
    command: LCDCommand | MotorCommand | None = Field(description="Command to be executed, can be LCDCommand or MotorCommand, or None for stop command")
    pause_duration: int = Field(default=0, description="Pause duration in seconds after executing the command (AI Command ONLY)")
    duration: int = Field(default=0, description="Duration in seconds for which the command should be executed (AI Command ONLY)")

    def __init__(self, **data):
        super().__init__(**data)
        self.ID = str(uuid.uuid4())
        
    @staticmethod
    def apply_deadzone_and_scale(value, deadzone=0.1, min_speed=60, max_speed=255):
        if abs(value) < deadzone:
            return 0
        
        sign = 1 if value > 0 else -1
        scaled = (abs(value) - deadzone) / (1 - deadzone)
        scaled = min(1, max(0, scaled))  # Clamp to [0, 1]
        
        return int(sign * (min_speed + scaled*(max_speed - min_speed)))
        
    
    @classmethod
    async def send_from_joystick(cls, left_y: float, right_x: float, ser: 'SerialManager'):
        """
        Calculate the differential drive values based on the controller input.
        """
        
        
        forward = cls.apply_deadzone_and_scale(left_y)
        turn = cls.apply_deadzone_and_scale(right_x)
        
        # Calculate motor values (arcade drive)
        left_motor = min(255, max(-255, forward - turn))
        right_motor = min(255, max(-255, forward + turn))

        command = cls(
            ID="",
            command_type=CommandType.MOTOR,
            command=MotorCommand(
                left_motor=left_motor,
                right_motor=right_motor,
            ),
            pause_duration=0,
            duration=0
        )

        ser.send(command)
        
    @classmethod
    async def stop(cls, ser: 'SerialManager'):
        """
        Send a stop command to the robot.
        """
        command = cls(
            ID="",
            command_type=CommandType.STOP,
            command=None,  # Stop command has no specific motor values
            pause_duration=0,
            duration=0
        )
        
        ser.send(command)
    
    
