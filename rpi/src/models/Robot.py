import time, threading
import asyncio
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
        self.sending_command = False # Flag to prevent requesting sensor data while sending a command
        self.sensor_request_interval = 0.1  # 10Hz = 0.1 seconds
        self.sensor_request_task = None
        self.running = False

    async def start(self):
        """Start the robot's background tasks"""
        self.running = True
        self.sensor_request_task = asyncio.create_task(self._sensor_request_loop())

    async def stop(self):
        """Stop the robot's background tasks"""
        self.running = False
        if self.sensor_request_task:
            self.sensor_request_task.cancel()
            try:
                await self.sensor_request_task
            except asyncio.CancelledError:
                pass

    async def _sensor_request_loop(self):
        """Background task to request sensor data at 10Hz"""
        while self.running:
            try:
                if not self.sending_command:
                    # Send "SENSOR" command to Arduino to request sensor data
                    sensor_request_command = Command(
                        command_type=CommandType.SENSOR,
                        command=None,
                        pause_duration=0,
                        duration=0
                    )
                    self.serial.send(sensor_request_command)
                await asyncio.sleep(self.sensor_request_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in sensor request loop: {e}")
                await asyncio.sleep(self.sensor_request_interval)

    async def _reset_cliff_detected(self):
        await asyncio.sleep(0.5)
        self.cliff_detected = False

    async def process_sensor_data(self, data: str):
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

                await self.socketio.emit(
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
            asyncio.create_task(self._reset_cliff_detected())  # Reset cliff detection after 0.5 seconds, basically halting commands
            await Command.send_from_joystick(0, 0, self.serial)  # Stop motors if cliff is detected

            if (not self.rumble_active) or (current_time - self.last_rumble_time > self.rumble_cooldown):
                await self.socketio.emit(
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
            await self.socketio.emit(
                'sensor_data',
                sensor_data.model_dump(),
            )


    async def handle_joystick_input(self, data):
        """
        Handle joystick input and send motor commands.
        """

        left_y = data.get('left_y', 0)
        right_x = data.get('right_x', 0)

        if not self.cliff_detected:
            self.sending_command = True
            await Command.send_from_joystick(left_y, right_x, self.serial)

    async def _run_command_sequence(self, commands):
        self.sending_command = True
        try:
            for command in commands.commands:
                self.serial.send(command)
                await asyncio.sleep(command.duration)
                if command.pause_duration and command.command_type == CommandType.MOTOR:
                    await Command.send_from_joystick(0, 0, self.serial)
                    await asyncio.sleep(command.pause_duration)
        finally:
            self.sending_command = False

    def handle_query(self, query):
        commands = text_to_command(query)

        command_task = asyncio.create_task(self._run_command_sequence(commands))
        return command_task