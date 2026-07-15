import logging, asyncio
from ..Bus import StateChange
from .. import ROBOT_CONFIG, Mode

class PathManager:
    def __init__(self, command_manager, world_model, bus):
        self.spline_path: Path | None = None
        self.dwa: DWA | None = None
        self.pure_pursuit: PurePursuit | None = None
        self.command_manager = command_manager
        self.world_model = world_model
        self.bus = bus
        self.last_path_time: float = 0.0
        self.last_dwa_time: float = 0.0
        
        self._logger = logging.getLogger("Robot.PathManager")

        self.path_following_dt = 1 / ROBOT_CONFIG.PATH_FOLLOWING_FREQ
        self.dwa_dt = 1 / ROBOT_CONFIG.DWA_FREQ
        
        self.bus.subscribe(
            StateChange,
            self.on_new_path
        )
    
    async def on_new_path(self, event: StateChange):
        if event.new_state != Mode.PATH_FOLLOWING:
            return

        if event.data["path_type"] == "spline":
            try:
                self.spline_path = Path.from_raw(event.data["path"]["splines"])
            except ValueError:
                await self.bus.publish(
                    PathError(reason="Invalid spline path")
                )
                self._logger.error("Invalid spline path")
        elif event.data["path_type"] == "freehand":
            self.pure_pursuit = PurePursuit.from_xy_points(event.data["path"])
        elif event.data["path_type"] == "point":
            self.dwa = DWA((event.data["path"]["x"], event.data["path"]["y"]), world_model=self.world_model)
        else:
            await self.bus.publish(
                PathError(reason=f"Unknown path type: {event.data['type']}")
            )

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
        self.spline_path = None
        self.pure_pursuit = None
        self.dwa = None
        
    async def execute_cur_path(self, robot_state: RobotState):
        if not (self.state_manager.get_state() == Mode.PATH_FOLLOWING):
            self.last_path_time = 0
            self.last_dwa_time = 0
            return
        
        if not asyncio.get_event_loop().time() - self.last_path_time >= self.path_following_dt:
            return
        
        if not self.cur_path_exists():
            await self.bus.publish(
                PathError(reason="No path exists")
            )
            return 
        
        exit_path = False
        error = ""
        
        if self.spline_path: # Quintic Hermite spline path using RAMSETE
            ready = self.spline_path.is_ready()
            
            if ready:
                if self.spline_path.complete():
                    exit_path = True
                else:
                    await self.command_manager.send_safe_command(self.spline_path.get_command(robot_state, asyncio.get_event_loop().time() - self.last_path_time))

        elif self.pure_pursuit:
            # Run pure pursuit
            command = self.pure_pursuit.calculate_control_command(robot_state)

            if not command:
                exit_path = True
            else:
                await self.command_manager.send_safe_command(command)

        elif self.dwa:
            if asyncio.get_event_loop().time() - self.last_dwa_time >= self.dwa_dt:
                command = self.dwa.calculate_control_command(self.state_estimator.state)

                if not command:
                    exit_path = True
                else:
                    await self.send_safe_command(command)

                self.last_dwa_time = asyncio.get_event_loop().time()
        else:
            exit_path = True
            error = ""

        if exit_path:
            await self.finish_path(error)

        self.last_path_time = asyncio.get_event_loop().time()
        