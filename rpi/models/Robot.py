import time
from . import SerialManager, SensorData, Command, CommandType, MotorCommand

class Robot:
    def __init__(self, serial_manager: SerialManager, socketio):
        self.serial = serial_manager
        self.last_emit_time = 0
        self.emit_interval = 0.1  # for sensor data
        self.last_rumble_time = 0
        self.rumble_cooldown = 1.0  # seconds between rumbles
        self.rumble_active = False
        self.socketio = socketio

    def process_sensor_data(self, data: str):
        sensor_data = SensorData.model_validate_json(data)

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

        Command.send_from_joystick(left_y, right_x, self.serial)
    
    def handle_query(self):
        """
        Handle a text query command to the robot.
        """
        pass
    
        
        
        