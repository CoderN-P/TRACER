from ..Bus import PathCompleted, PathError

class SocketManager:
    def __init__(self, socketio, state_manager, config_manager, manual_manager, bus):
        self.socketio = socketio
        
        self.state_manager = state_manager
        self.config_manager = config_manager
        self.manual_manager = manual_manager
        self.bus = bus
        
        self.bus.subscribe(
            PathCompleted,
            self.on_path_complete
        )
        
        self.bus.subscribe(
            PathError,
            self.on_path_error
        )
        
    async def on_path_complete(self, event: PathCompleted):
        await self.socket_manager.socketio.emit('path_complete', {"status": "success"})
        
    async def on_path_error(self, event: PathError):
        await self.socket_manager.socketio.emit('path_complete', {"status": "error", "message": event.message})
    
    async def process_socketio_command(self, event, data):
        match event:
            case 'set_state':
                await self.state_manager.set_state(data)
                return
            case 'stop':
                await self.state_manager.emergency_stop()
                return
            case 'enable':
                await self.state_manager.resume()
                return
            case 'query':
                # TODO: Implement proper LLM control
                pass
            case 'update_constants':
                await self.config_manager.update_constants(data)
                return
            case 'vel_command':
                await self.manual_manager.velocity_profile_manager.execute_velocity_profile()
            case 'joystick_input':
                await self.manual_manager.handle_joystick_input(data)  