import asyncio
from .Command import Command

class CommandManager:
    def __init__(self, serial):
        self.serial = serial
        self.last_command_sent_at = 0.0
        self.last_command_type = None
        self.last_command_id = None
        self.freeze_after_cmd_window_s: float = 0.5
        self.pending_motor_command: Command | None = None

    async def send_safe_command(self, command: Command, wait_after: float = 0):
        now = asyncio.get_event_loop().time()
        self.last_command_sent_at = now
        self.last_command_type = command.command_type.name if hasattr(command.command_type, "name") else str(command.command_type)
        self.last_command_id = command.ID
        self.serial.send(command)
        if wait_after > 0:
            await asyncio.sleep(wait_after)
                
    async def execute_pending_motor_command(self):
        print(self.pending_motor_command)
        if self.pending_motor_command:
            await self.send_safe_command(self.pending_motor_command)
            self.pending_motor_command = None
