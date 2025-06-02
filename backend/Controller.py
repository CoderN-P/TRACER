import pygame, threading, time

class Controller:
    def __init__(self, controller, socketio):
        self.controller = controller
        self.socketio = socketio # socketio client
        self.last_send_time = 0
        self.send_interval = 0.05  # seconds = 20Hz

    @classmethod
    def initialize(cls, socketio) -> 'Controller':
        pygame.joystick.init()

        if pygame.joystick.get_count() == 0:
            raise RuntimeError("No controllers found")

        controller = pygame.joystick.Joystick(0)
        controller.init()

        return cls(controller, socketio)

    def read_input(self) -> tuple:
        pygame.event.pump()
        left_y = self.controller.get_axis(1)
        right_x = self.controller.get_axis(2)

        return left_y, right_x

    def should_send_update(self) -> bool:
        """
        Check if the controller input is significant enough to send a command.
        """
        left_y, right_x = self.read_input()
        moved_enough = abs(left_y) > 0.1 or abs(right_x) > 0.1
        enough_time = (time.time() - self.last_send_time) > self.send_interval
        return moved_enough and enough_time
    
    def send_update(self):
        """
        Send the current joystick data to the specified URL.
        """

        if not self.should_send_update():
            return 
        
        left_y, right_x = self.read_input()
        
        data = {
            "left_y": left_y,
            "right_x": right_x
        }
        
        try:
            self.socketio.emit('joystick_input', data)
        except Exception as e:
            raise RuntimeError(f"Failed to send controller update: {e}")


    def rumble(self, low, high, duration_ms):
        self.controller.rumble(low, high, duration_ms)
    
        # Stop after duration using a background timer
        duration_sec = duration_ms / 1000
        threading.Timer(duration_sec, self.controller.stop_rumble).start()
        
        
        
            
            
        
        
        
        
        
        

        
        