import asyncio
import time

from .Command import Command

class CommandManager:
    def __init__(self, serial):
        self.serial = serial
        self.command_lock = asyncio.Lock()
        self.last_command_sent_at = 0.0
        self.last_command_type = None
        self.last_command_id = None
        self.freeze_after_cmd_window_s: float = 0.5
        self.pending_motor_command: Command | None = None

    async def send_safe_command(self, command: Command, wait_after: float = 0):
        async with self.command_lock:
            self._send_locked(command)
        if wait_after > 0:
            await asyncio.sleep(wait_after)

    def _send_locked(self, command: Command):
        now = time.monotonic()
        self.last_command_sent_at = now
        self.last_command_type = command.command_type.name if hasattr(command.command_type, "name") else str(command.command_type)
        self.last_command_id = command.ID
        self.serial.send(command)

    async def get_last_command_info(self):
        async with self.command_lock:
            return {
                "sent_at": self.last_command_sent_at,
                "type": self.last_command_type,
                "id": self.last_command_id,
                "freeze_after_cmd_window_s": self.freeze_after_cmd_window_s,
            }

    async def set_pending_motor_command(self, command: Command | None):
        async with self.command_lock:
            self.pending_motor_command = command
                
    async def execute_pending_motor_command(self):
        async with self.command_lock:
            command = self.pending_motor_command
            self.pending_motor_command = None

            if command:
                self._send_locked(command)
