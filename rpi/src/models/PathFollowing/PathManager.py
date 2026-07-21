import logging, asyncio, time
from .. import ROBOT_CONFIG, Mode
from .PurePursuit import PurePursuit
from .Path import Path
from .DWA import DWA
from ..Bus import PathError, StateChange, PathCompleted
from ..Command import Command

class PathManager:
    def __init__(self, command_manager, world_model, state_manager, bus):
        self.spline_path: Path | None = None
        self.dwa: DWA | None = None
        self.pure_pursuit: PurePursuit | None = None
        self.path_lock = asyncio.Lock()
        self.command_manager = command_manager
        self.state_manager = state_manager
        self.world_model = world_model
        self.bus = bus
        self.last_dwa_time: float = 0.0
        
        self._logger = logging.getLogger("Robot.PathManager")
        
        self.dwa_dt = 1 / ROBOT_CONFIG.DWA_FREQ
        
        self.bus.subscribe(
            StateChange,
            self.on_new_path
        )
    
    async def on_new_path(self, event: StateChange):
        if event.new_state != Mode.PATH_FOLLOWING:
            return

        path_error = None
        async with self.path_lock:
            self.spline_path = None
            self.pure_pursuit = None
            self.dwa = None

            if event.data["path_type"] == "spline":
                try:
                    self.spline_path = Path.from_raw(event.data["path"]["splines"])
                except ValueError:
                    path_error = "Invalid spline path"
                    self._logger.error("Invalid spline path")
            elif event.data["path_type"] == "freehand":
                self.pure_pursuit = PurePursuit.from_xy_points(event.data["path"])
            elif event.data["path_type"] == "point":
                self.dwa = DWA((event.data["path"]["x"], event.data["path"]["y"]), world_model=self.world_model)
            else:
                path_error = f"Unknown path type: {event.data['type']}"

        if path_error:
            await self.bus.publish(PathError(reason=path_error))

    def cur_path_exists(self):
        if self.spline_path:
            return True
        if self.dwa:
            return True
        if self.pure_pursuit:
            return True
        
        return False
    
    async def finish_path(self, error: str):
        await self.command_manager.send_safe_command(Command.stop())
        if error:
            await self.bus.publish(
                PathError(reason=error)
            )
        else:
            await self.bus.publish(
                PathCompleted()
            )
        async with self.path_lock:
            self.spline_path = None
            self.pure_pursuit = None
            self.dwa = None
        
    async def execute_cur_path(self, robot_state):
        if not (await self.state_manager.get_state() == Mode.PATH_FOLLOWING):
            async with self.path_lock:
                self.last_dwa_time = 0
            return

        exit_path = False
        error = ""

        async with self.path_lock:
            if not self.cur_path_exists():
                error = "No path exists"
                exit_path = True

            elif self.spline_path: # Quintic Hermite spline path using RAMSETE
                ready = self.spline_path.is_ready()
                
                if ready:
                    if self.spline_path.complete():
                        exit_path = True
                    else:
                        await self.command_manager.send_safe_command(self.spline_path.get_command(robot_state, time.monotonic() - self.last_dwa_time))

            elif self.pure_pursuit:
                # Run pure pursuit
                command = self.pure_pursuit.calculate_control_command(robot_state)
                if not command:
                    exit_path = True
                else:
                    await self.command_manager.send_safe_command(command)

            elif self.dwa:
                if time.monotonic() - self.last_dwa_time >= self.dwa_dt:
                    command = self.dwa.calculate_control_command(robot_state)

                    if not command:
                        exit_path = True
                    else:
                        await self.command_manager.send_safe_command(command)

                    self.last_dwa_time = time.monotonic()
            else:
                exit_path = True

        if exit_path:
            await self.finish_path(error)
        
