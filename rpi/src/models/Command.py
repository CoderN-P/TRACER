from pydantic import BaseModel, Field
import uuid
from .LCDCommand import LCDCommand
from .MotorCommand import MotorCommand
from .CommandTypeEnum import CommandType
from .SerialManager import SerialManager



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


    @classmethod
    async def send_from_joystick(cls, left_y: float, right_x: float, ser: SerialManager):
        """
        Calculate the differential drive values based on the controller input.
        """
        if abs(left_y) < 0.1: left_y = 0
        if abs(right_x) < 0.1: right_x = 0

        # Calculate motor values (arcade drive)
        left_motor = int(255 * (left_y - right_x))
        right_motor = int(255 * (left_y + right_x))

        # Clamp values
        left_motor = max(-255, min(255, left_motor))
        right_motor = max(-255, min(255, right_motor))

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

        await ser.send(command)
    
    