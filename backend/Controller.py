import pygame, threading

class Controller:
    def __init__(self, controller, socketio, socketio_server):
        self.controller = controller
        self.socketio = socketio # socketio client
        self.socketio_server = socketio_server # socketio server
        self.reset_motor = False

    @classmethod
    def initialize(cls, socketio, socketio_server) -> 'Controller':
        pygame.init()
        pygame.joystick.init()

        if pygame.joystick.get_count() == 0:
            raise RuntimeError("No controllers found")

        controller = pygame.joystick.Joystick(0)
        controller.init()

        return cls(controller, socketio, socketio_server)

    def read_input(self) -> tuple:
        pygame.event.pump()  # Process events to update joystick state
        left_y = -self.controller.get_axis(1)
        right_x = -self.controller.get_axis(2)

        return left_y, right_x

    def should_send_update(self) -> bool:
        """
        Check if the controller input is significant enough to send a command.
        """
        left_y, right_x = self.read_input()
        moved_enough = abs(left_y) > 0.1 or abs(right_x) > 0.1
        return moved_enough

    
    def send_update(self):
        """
        Send the current joystick data to the specified URL.
        """

        if not self.should_send_update():
            if self.reset_motor:
                # If no significant input, reset motors
                self.reset_motor = False
                data = {
                    "left_y": 0,
                    "right_x": 0
                }
            else:
                # If no significant input and not resetting, do nothing
                return
                
        else: 
            left_y, right_x = self.read_input()
        
            data = {
                "left_y": left_y,
                "right_x": right_x
            }
            
            self.reset_motor = True  # Set flag to reset motors next time if no input
    
        
        try:
            self.socketio_server.emit('joystick_input', data)
            self.socketio.emit('joystick_input', data)
        except Exception as e:
            raise RuntimeError(f"Failed to send controller update: {e}")
        
    def handle_joystick_input(self, data):
        """
        Handle joystick input from the UI.
        """
        left_y = data.get('left_y', 0)
        right_x = data.get('right_x', 0)

        self.socketio.emit('joystick_input', {
            "left_y": -left_y,
            "right_x": -right_x
        })


    def rumble(self, low, high, duration_ms):
        self.controller.rumble(low, high, duration_ms)
    
        # Stop after duration using a background timer
        duration_sec = duration_ms / 1000
        threading.Timer(duration_sec, self.controller.stop_rumble).start()
