from pydantic import BaseModel, Field
import uuid
from .LCDCommand import LCDCommand
from .MotorCommand import MotorCommand
from .CommandTypeEnum import CommandType



class Command(BaseModel):
    """
    Represents a command to be executed by the robot.
    """
    ID: str = Field(description="Unique identifier for the command")
    command_type: CommandType
    command: LCDCommand | MotorCommand | None = Field(description="Command to be executed, can be LCDCommand or MotorCommand, or None for stop command")
    pause_duration: int = Field(description="Pause duration in seconds after executing the command (AI Command ONLY)")
    duration: int = Field(description="Duration in seconds for which the command should be executed (AI Command ONLY)")

    def __init__(self, **data):
        super().__init__(**data)
        self.ID = str(uuid.uuid4())
        
    @staticmethod
    def scale(value):
        wheel_diameter = 0.05 # in m
        max_rpm = 178 # Max RPM of the motor
        max_speed = (wheel_diameter * 3.1416 * max_rpm) / 60 # V = r*omega
        
        sign = 1 if value > 0 else -1
        scaled = min(1, max(0, abs(value)))  # Clamp to [0, 1]
        
        return int(sign * (scaled*max_speed))
        
    
    @classmethod
    def from_joystick(cls, left_y: float, right_x: float):
        """
        Calculate the differential drive values based on the controller input.
        """
        wheel_diameter = 0.05 # in m
        max_rpm = 178 # Max RPM of the motor
        max_speed = (wheel_diameter * 3.1416 * max_rpm) / 60 # V = r*omega
        
        forward = cls.apply_deadzone_and_scale(left_y)
        turn = cls.apply_deadzone_and_scale(right_x)
        
        # Calculate motor values (arcade drive)
        left_motor = min(max_speed, max(-max_speed, forward - turn))
        right_motor = min(max_speed, max(-max_speed, forward + turn))

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

        return command
    
    @classmethod
    def enable(cls):
        """
        Create an enable command to enable motors after estop.
        """
        command = cls(
            ID="",
            command_type=CommandType.ENABLE,
            command=None,  # Enable command has no specific motor values
            pause_duration=0,
            duration=0
        )
        
        return command
    
    @classmethod
    def stop(cls):
        """
        Create a stop command with zero motor values.
        """
        command = cls(
            ID="",
            command_type=CommandType.MOTOR,
            command=MotorCommand(
                left_motor=0,
                right_motor=0,
            ),
            pause_duration=0,
            duration=0
        )
        
        return command
    
    
    @classmethod
    def estop(cls):
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
        
        return command
    
    
