import logging, asyncio
from .Bus import PathError, PathCompleted, StateChange
from .Command import Command
from .Mapping import LocalizationMode
from . import Mode, MetaMode, NavigationMode
from .SensorData import SensorData

class StateManager:
    def __init__(self, command_manager, bus):
        self.state: Mode = Mode.MANUAL
        self.navigation_state: NavigationMode = NavigationMode.MANUAL
        self.meta_state: MetaMode = MetaMode.USER
        self.localization_state: LocalizationMode = LocalizationMode.MAP
        self.state_lock: asyncio.Lock = asyncio.Lock()  # Lock to protect access to the robot's state (manual, autonomous, stopped)
        self._logger = logging.getLogger("Robot.StateManager")
        self.command_manager = command_manager
        self.bus = bus
        self.state_lock = asyncio.Lock()
        
        self.bus.subscribe(PathCompleted, self.on_finish_path)
        self.bus.subscribe(PathError, self.on_finish_path)

    async def set_state(self, data):
        """Set the robot's state (manual, path following, stopped)"""
        async with self.state_lock:
            cur_state = self.state
            next_state = Mode[data["state"]]

            if next_state == Mode.PATH_FOLLOWING:
                self.state = Mode.PATH_FOLLOWING
                event = StateChange(prev_state=cur_state, new_state=next_state, data=data)
                action = None
            elif next_state == Mode.MANUAL:
                if cur_state == Mode.STOPPED:
                    event = None
                    action = self.resume
                else:
                    self.state = next_state
                    event = StateChange(prev_state=cur_state, new_state=next_state)
                    action = None
            elif next_state == Mode.STOPPED:
                event = None
                action = self.emergency_stop
            else:
                event = None
                action = None

        if event:
            await self.bus.publish(event)
        if action:
            await action()

    async def on_finish_path(self, event):
        await self.set_state({"state": "MANUAL"})

    async def emergency_stop(self):
        """Immediately stop the robot and clear any pending commands."""
        async with self.state_lock:
            prev_state = self.state
            self.state = Mode.STOPPED

        await self.bus.publish(
            StateChange(prev_state=prev_state, new_state=Mode.STOPPED)
        )
        await self.command_manager.send_safe_command(Command.estop())

    async def resume(self):
        """Resume normal operation after an emergency stop."""
        async with self.state_lock:
            prev_state = self.state
            self.state = Mode.MANUAL

        await self.bus.publish(
            StateChange(prev_state=prev_state, new_state=Mode.MANUAL)
        )
        await self.command_manager.send_safe_command(Command.stop())   # clear any stale setpoint
        await self.command_manager.send_safe_command(Command.enable())
    
    async def get_state(self):
        """Get the robot's current state (manual, path following, stopped)"""
        async with self.state_lock:
            return self.state

    async def get_localization_state(self):
        async with self.state_lock:
            return self.localization_state
            
    
