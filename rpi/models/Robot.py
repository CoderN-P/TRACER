import time, threading
from . import SerialManager, SensorData, Command, CommandType, MotorCommand
from ..ai.get_commands import text_to_command


class Robot:
    def __init__(self, serial_manager: SerialManager, socketio):
        self.serial = serial_manager
        self.last_emit_time = 0
        self.emit_interval = 0.1  # for sensor data
        self.last_rumble_time = 0
        self.rumble_cooldown = 1.0  # seconds between rumbles
        self.rumble_active = False
        self.socketio = socketio
        self.cliff_detected = False

    def process_sensor_data(self, data: str):
        try:
            sensor_data = SensorData.model_validate_json(data)

        except Exception as e:
            print(f"Error processing sensor data: {e}")
            return

        current_time = time.time()

        if sensor_data.is_obstacle_detected():
            if (not self.rumble_active) or (current_time - self.last_rumble_time > self.rumble_cooldown):
                distance = sensor_data.ultrasonic.distance
                low = distance / 10
                high = 1 - low

                self.socketio.emit(
                    'rumble',
                    {
                        "low": low,
                        "high": high,
                        "duration": 1000,
                    }
                )
                self.last_rumble_time = current_time
                self.rumble_active = True
        else:
            self.rumble_active = False  # Reset so future detections can trigger rumble again
            
        # Check for cliff detection
        if sensor_data.check_cliff() and not self.cliff_detected:
            self.cliff_detected = True
            threading.Timer(0.5, lambda: setattr(self, 'cliff_detected', False)).start()  # Reset cliff detection after 5 seconds, basically halting commands
            Command.send_from_joystick(0, 0, self.serial)  # Stop motors if cliff is detected
            
            if (not self.rumble_active) or (current_time - self.last_rumble_time > self.rumble_cooldown):
                self.socketio.emit(
                    'rumble',
                    {
                        "low": 0.5,
                        "high": 0.5,
                        "duration": 1000,
                    }
                )
                self.last_rumble_time = current_time
                self.rumble_active = True
            

        # Emit sensor data at a fixed interval
        if current_time - self.last_emit_time >= self.emit_interval:
            self.last_emit_time = current_time
            self.socketio.emit(
                'sensor_data',
                sensor_data.model_dump_json(),
            )
            
    
    def handle_joystick_input(self, data):
        """
        Handle joystick input and send motor commands.
        """
        
        left_y = data.get('left_y', 0)
        right_x = data.get('right_x', 0)
        
        if not self.cliff_detected:
            Command.send_from_joystick(left_y, right_x, self.serial)

    def _run_command_sequence(self, commands):
        for command in commands.commands:
            self.serial.send(command)
            time.sleep(command.duration)
            if command.pause_duration and command.command_type == CommandType.MOTOR:
                Command.send_from_joystick(0, 0, self.serial)
                time.sleep(command.pause_duration)
                    
    def handle_query(self, query):
        commands = text_to_command(query)

        command_thread = threading.Thread(target=self._run_command_sequence, args=(commands,))
        command_thread.daemon = True  # Ensure thread exits when main program exits
        command_thread.start()
        return command_thread
