from typing import List, Dict
import time
import asyncio
from ..Mode import Mode
from ..Command import Command, TwistCommand, MotorCommand, CommandType, MotorPWMCommand

class VelocityProfileManager:
    def __init__(self, command_manager = None, state_manager = None):
        self.velocity_profile_start: float = 0.0
        self.command_manager = command_manager
        self.state_manager = state_manager

    async def execute_velocity_profile(self, profile: List[Dict], mode: str = 'wheel'):
        if len(profile) < 2:
            return

        self.velocity_profile_start = time.monotonic()

        i = 0
        t_start = asyncio.get_event_loop().time()

        while True:
            t = asyncio.get_event_loop().time() - t_start
            if t >= profile[-1]["t"]:
                break

            starting_point = None

            for j in range(i, len(profile) - 1):
                if profile[j]["t"] <= t <= profile[j+1]["t"]:
                    starting_point = j
                    break

            if starting_point is None:
                # Only possible cause is that the first point in the profile is ahead of the current t, in that case just send 0
                await self.execute_velocity_command(0, 0, mode=mode)
            else:
                i = starting_point
                p0 = profile[i]
                p1 = profile[i + 1]

                # Linear interpolation
                v1 = (p1['v1'] - p0['v1']) / (p1['t'] - p0['t']) * (t - p0["t"]) + p0['v1']
                v2 = (p1['v2'] - p0['v2']) / (p1['t'] - p0['t']) * (t - p0["t"]) + p0['v2']
                await self.execute_velocity_command(v1, v2, mode=mode) # Sets vel command to pending

            await asyncio.sleep(0.02)
            t += 0.02

        self.velocity_profile_start = None
        self.command_manager.pending_motor_command = Command.stop()


    async def execute_velocity_command(self, v1: float, v2: float, mode: str = 'wheel'):
        if await self.state_manager.get_state() in [Mode.STOPPED, Mode.PATH_FOLLOWING]:
            return

        if mode == 'twist':
            self.pending_motor_command = Command(
                ID="",
                command_type=CommandType.TWIST,
                command=TwistCommand(
                    v=v1,
                    omega=v2,
                ),
                pause_duration=0,
                duration=0,
            )

        elif mode == 'pwm':
            self.command_manager.pending_motor_command = Command(
                ID="",
                command_type=CommandType.PWM,
                command=MotorPWMCommand(
                    left_motor=v1,
                    right_motor=v2
                ),
                pause_duration=0,
                duration=0,
            )
        else:
            self.command_manager.pending_motor_command = Command(
                ID="",
                command_type=CommandType.MOTOR,
                command=MotorCommand(
                    left_motor=v1,
                    right_motor=v2
                ),
                pause_duration=0,
                duration=0,
            )
