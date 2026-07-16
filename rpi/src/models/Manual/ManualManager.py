import logging
import asyncio 

from . import VelocityProfileManager
from .. import ROBOT_CONFIG
from ..Mode import Mode
from ..Command.Command import Command

class ManualManager:
    def __init__(self, command_manager, state_manager):
        self.command_manager = command_manager
        self.state_manager = state_manager
        self.last_manual_time: float = 0.0
        
        self.manual_dt = 1 / ROBOT_CONFIG.MANUAL_FREQ
        self._logger = logging.getLogger("Robot.ManualManager")
        
        self.velocity_profile_manager = VelocityProfileManager(command_manager, state_manager) # Handles execution of manual velocity profiles


    async def handle_joystick_input(self, data):
        """
        Handle joystick input and send motor commands.
        """

        cur_state = await self.state_manager.get_state()

        if cur_state != Mode.MANUAL:
            return

        left_y = data.get('left_y', 0)
        right_x = data.get('right_x', 0)


        if data.get("type"):
            motor_command = Command.from_joystick(left_y, right_x, data["type"])
        else:
            motor_command = Command.from_joystick(left_y, right_x)

        self.command_manager.pending_motor_command = motor_command
        """
        if self.obstacle_clear.is_set():
            self.command_manager.pending_motor_command = motor_command
        else:
            # Check if motor command has 0 or negative linear velocity
            linear_vel = (motor_command.command.left_motor + motor_command.command.left_motor) / 2

            if linear_vel > 0:
                self._logger.info("Skipping command to avoid crashing")
            else:
                self.command_manager.pending_motor_command = motor_command
        """                
                
    async def execute_manual_commands(self):
        if await self.state_manager.get_state() != Mode.MANUAL:
            self.last_manual_time = 0
            return
                
        if asyncio.get_event_loop().time() - self.last_manual_time >= self.manual_dt:
            await self.command_manager.execute_pending_motor_command()
            self.last_manual_time = asyncio.get_event_loop().time()
            
    
