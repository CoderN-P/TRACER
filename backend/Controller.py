import datetime
import math, pygame, threading, time

from ControllerState import ControllerState


class Controller:
    def __init__(self, controller, socketio, socketio_server):
        self.controller = controller
        self.socketio = socketio  # socketio client
        self.socketio_server = socketio_server  # socketio server

        # --- Feature flags ---
        self.reset_motor = True  # Flag to reset motors if no input is detected
        self.stop_motor = False  # Flag to stop motors if no input is detected
        self.stopped = False  # Flag to indicate if the motors are stopped
        self.state = ControllerState.TWO_ARCADE
        self.precision_mode = False  # Flag to indicate if precision mode is enabled
        self.speed = 0  # Car speed, used in CAR state
        self.reconnecting = False  # Flag to indicate if the controller is being reconnected
        self.recording = False  # Flag to indicate if the controller is recording
        self.playing_recording = False  # Flag to indicate if the controller is playing a recording

        # --- Cooldown flags ---
        self.state_cooldown = False  # Cooldown to prevent rapid state switching
        self.precision_mode_cooldown = False  # Cooldown to prevent rapid precision mode switching
        self.recording_cooldown = False  # Cooldown to prevent rapid recording toggling
        self.playing_recording_cooldown = False  # Cooldown to prevent rapid playback toggling

        # --- Joystick history ---
        self.joystick_history = []  # List to store joystick history for recording

    @classmethod
    def initialize(cls, socketio, socketio_server) -> 'Controller':
        pygame.init()
        pygame.joystick.init()

        if pygame.joystick.get_count() == 0:
            threading.Thread(cls.reconnect_controller()).start()

        controller = pygame.joystick.Joystick(0)
        controller.init()

        return cls(controller, socketio, socketio_server)

    def reconnect_controller(self):
        """
        Reconnect the controller if it has been disconnected in a thread
        """

        while pygame.joystick.get_count() == 0:
            print("No controller found, trying to reconnect...")
            pygame.joystick.quit()  # Quit the joystick module to reset it
            pygame.joystick.init()  # Reinitialize the joystick module
            try:
                self.controller = pygame.joystick.Joystick(0)
                self.controller.init()
                self.reconnecting = False  # Reset reconnecting flag
                print("Controller reconnected successfully")
                return
            except pygame.error:
                print("Failed to reconnect controller, retrying...")
            time.sleep(1)  # Wait before trying again

    def read_input(self) -> tuple:
        pygame.event.pump()  # Process events to update joystick state

        if self.state == ControllerState.TWO_ARCADE:
            left_y = -self.controller.get_axis(1)
            right_x = -self.controller.get_axis(2)
        elif self.state == ControllerState.ONE_ARCADE:
            left_y = -self.controller.get_axis(1)
            right_x = -self.controller.get_axis(0)
        else:  # TANK
            left = -self.controller.get_axis(1)
            right = -self.controller.get_axis(3)

            left_y = (left + right) / 2
            right_x = (right - left) / 2

        return left_y, right_x

    def should_send_update(self) -> bool:
        """
        Check if the controller input is significant enough to send a command.
        """
        if self.state == ControllerState.CAR:
            # In CAR state, we consider the speed to determine if we should send an update
            return abs(self.speed) > 0.15

        left_y, right_x = self.read_input()
        moved_enough = abs(left_y) > 0.15 or abs(right_x) > 0.15
        return moved_enough

    def _reset_stop_motor(self):
        """
        Reset the stop motor flag after a short delay.
        """

        def reset():
            self.stopped = False

        threading.Timer(5, reset).start()

    def _reset_cooldown(self, attr):
        """
        Generic cooldown reset helper.
        """
        setattr(self, attr, False)

    def play_recording(self, timestamp=None):
        if len(self.joystick_history) == 0:
            print("No recording to play")
            return

        if self.recording:
            print("Cannot play recording while recording is active")

            return
        if not timestamp:
            entry = self.joystick_history[-1]
            self.socketio_server.emit('start_playback', {
                "timestamp": entry.get("timestamp", datetime.datetime.now().isoformat()),
                "duration": len(entry["commands"]) / 20  # 20 Hz playback rate
            })
        else:
            # Find the entry with the matching timestamp
            entry = next((e for e in self.joystick_history if e.get("timestamp") == timestamp), None)
            if not entry:
                self.socketio_server.emit('playback_error', {
                    "error": "No recording found with the specified timestamp"
                })
                return

            self.socketio_server.emit('start_playback', {
                "timestamp": entry.get("timestamp", timestamp),
                "duration": len(entry["commands"]) / 20  # 20 Hz playback rate
            })

        self.playing_recording = True
        commands = entry.get("commands", [])

        for command in commands:
            # Emit each command with a delay to simulate real-time playback
            if not self.playing_recording:
                self.socketio.emit('stop', {})
                self.socketio_server.emit('playback_stopped', {})
                return

            self.socketio_server.emit('joystick_input', command)
            self.socketio.emit('joystick_input', command)
            time.sleep(0.05)  # 20 Hz playback rate same as the main loop

        self.socketio.emit('stop', {})
        self.socketio_server.emit('joystick_input', {
            "left_y": 0,
            "right_x": 0
        })
        self.socketio_server.emit('playback_stopped', {})

    def is_button_ready(self, button_index, cooldown_attr, duration=0.5):
        """
        Helper to check if a button is pressed and its cooldown is not active.
        Sets the cooldown and schedules its reset if pressed.
        """
        if getattr(self, cooldown_attr):
            return False
        if self.controller.get_button(button_index):
            setattr(self, cooldown_attr, True)
            threading.Timer(duration, self._reset_cooldown, args=(cooldown_attr,)).start()
            return True
        return False

    def stop_recording(self):
        """
        Stop the current recording and reset the recording flag.
        """
        if not self.recording:
            print("No recording is currently active")
            return

        self.recording = False
        self.socketio_server.emit('stop_recording', {
            "timestamp": self.joystick_history[-1].get("timestamp", datetime.datetime.now().isoformat()),
            "duration": len(self.joystick_history[-1]["commands"]) / 20  # 20 Hz playback rate
        })
        self.rumble(0.5, 0.5, 500)  # Rumble to indicate recording stopped

    def start_recording(self):
        """
        Start a new recording session.
        """
        if self.recording:
            return

        self.recording = True
        self.joystick_history.append({
            "commands": [],
            "timestamp": datetime.datetime.now().isoformat()
        })
        self.rumble(0.5, 0.5, 500)  # Rumble to indicate recording started
        self.socketio_server.emit('start_recording', {})

    def toggle_precision_mode(self):
        """
        Toggle the precision mode on or off.
        """

        self.precision_mode = not self.precision_mode
        self.socketio_server.emit("precision_mode", {"enabled": self.precision_mode})
        self.rumble(0.5, 0.5, 500)

    def manage_state(self, new_state: str = None):
        if new_state:  # called from UI
            if new_state == "TWO_ARCADE":
                self.state = ControllerState.TWO_ARCADE
            elif new_state == "ONE_ARCADE":
                self.state = ControllerState.ONE_ARCADE
            elif new_state == "TANK":
                self.state = ControllerState.TANK
            elif new_state == "CAR":
                self.state = ControllerState.CAR
            else:
                print(f"Unknown state: {new_state}")
                return
            self.socketio_server.emit("joystick_mode", {"mode": self.state.name})
            self.rumble(0.5, 0.5, 500)
        else:
            if self.is_button_ready(10, 'state_cooldown'):
                if self.state == ControllerState.TWO_ARCADE:
                    self.state = ControllerState.ONE_ARCADE
                elif self.state == ControllerState.ONE_ARCADE:
                    self.state = ControllerState.TANK
                elif self.state == ControllerState.TANK:
                    self.state = ControllerState.CAR
                elif self.state == ControllerState.CAR:
                    self.state = ControllerState.TWO_ARCADE
                self.rumble(0.5, 0.5, 500)
                self.socketio_server.emit("joystick_mode", {"mode": self.state.name})
            elif self.is_button_ready(9, 'state_cooldown'):
                if self.state == ControllerState.TWO_ARCADE:
                    self.state = ControllerState.CAR
                elif self.state == ControllerState.ONE_ARCADE:
                    self.state = ControllerState.TWO_ARCADE
                elif self.state == ControllerState.TANK:
                    self.state = ControllerState.ONE_ARCADE
                elif self.state == ControllerState.CAR:
                    self.state = ControllerState.TANK
                self.rumble(0.5, 0.5, 500)
                self.socketio_server.emit("joystick_mode", {"mode": self.state.name})

    def send_update(self):
        """
        Send the current joystick data to the specified URL.
        """
        # check if Button B is pressed to reset motors
        if pygame.joystick.get_count() == 0 and not self.reconnecting:
            self.reconnecting = True
            threading.Thread(self.reconnect_controller()).start()

        pygame.event.pump()  # Process events to update joystick state
        if self.controller.get_button(1):  # Button B is at index 1
            if self.stop_motor:
                self.socketio.emit('stop', {})
                self.socketio_server.emit('stop', {})
                print("Stopping motors due to Button B press")
                self.stop_motor = False  # Reset flag to avoid sending stop command repeatedly
                self.stopped = True
                self._reset_stop_motor()
            return
        else:
            self.stop_motor = True

        # left and right bumpers for switching states
        pygame.event.pump()  # Process events to update joystick state

        # Precision mode toggle (Y button, index 3)
        if self.is_button_ready(3, 'precision_mode_cooldown'):
            self.toggle_precision_mode()

        # State toggle (left bumper, index 9) and (right bumper, index 10)
        self.manage_state()

        # Playback toggle (A button, index 0)
        if self.is_button_ready(0, 'playing_recording_cooldown'):
            self.rumble(0.5, 0.5, 500)
            if self.playing_recording:
                self.playing_recording = False
            else:
                threading.Thread(self.play_recording()).start()

        # Recording toggle (X button, index 2)
        if self.is_button_ready(2, 'recording_cooldown', duration=1):
            self.rumble(0.5, 0.5, 500)
            if not self.recording:
                self.start_recording()
            else:
                self.stop_recording()

        if self.stopped:
            return

        if self.state == ControllerState.CAR:
            left_trigger = (self.controller.get_axis(4) + 1) / 2
            right_trigger = (self.controller.get_axis(5) + 1) / 2

            # Increase speed with left trigger (accelerator)
            if left_trigger > 0.1:
                self.speed += 0.05 * left_trigger
            # Decrease speed with right trigger (brake)
            if right_trigger > 0.1:
                self.speed -= 0.05 * right_trigger
                
            if left_trigger < 0.1 and right_trigger < 0.1:
                self.speed -= 0.01  # Slow down if no trigger is pressed

            # Clamp speed between -1 and 1 to allow reverse
            self.speed = max(0, min(self.speed, 1))

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
            if self.state == ControllerState.CAR:
                # In CAR state, we send the speed directly

                x = -self.controller.get_axis(0)
                y = -self.controller.get_axis(1)

                magnitude = math.sqrt(x ** 2 + y ** 2)
                print(f"Joystick magnitude: {magnitude}, x: {x}, y: {y}")

                # x and y must have 1 magnitude
                # even if x and y are 0, 0 we still move straight since we only care about joystick direction
                if magnitude > 0.1:
                    x /= magnitude
                    y /= magnitude
                else:
                    x = 0
                    y = 1  # Default to forward if joystick is centered

                left_y = y * self.speed
                right_x = x * self.speed
            else:
                left_y, right_x = self.read_input()

            if self.precision_mode:
                # Scale down the input for precision mode
                left_y *= 0.5
                right_x *= 0.5

            data = {
                "left_y": left_y,
                "right_x": right_x
            }

            if self.recording:
                self.joystick_history[-1]["commands"].append(data)

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
