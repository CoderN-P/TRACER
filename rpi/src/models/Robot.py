import logging
import time, struct
import asyncio
from . import SerialManager, SensorData, Command, CommandType, LCDCommand
from ..ai.get_commands import text_to_command


class Robot:
    def __init__(self, serial_manager: SerialManager, socketio):
        self.serial = serial_manager
        self.last_emit_time = 0
        self.emit_interval = 0.1  # for sensor data
        self.last_rumble_time = 0
        self.rumble_cooldown = 1  # seconds between rumbles
        self.socketio = socketio
        self.cliff_detected = False
        self.waiting_for_sensor = asyncio.Event()
        self.sensor_request_interval = 0.1  # 10Hz = 0.1 seconds
        self.sensor_request_task = None
        self.running = False
        self.distance_history = []  # Store last 10 distances
        self.sensor_count = 0  # Count of sensor data received
        self.last_sensor_request_time = 0  # Last time sensor data was requested
        self.obstacle_detected = False  # Flag to indicate if an obstacle is detected
        self.backup_time = 2  # Amount of time to backup when an obstacle is detected
        self.obstacle_threshold = 20 # Distance threshold for obstacle detection
        self._logger = logging.getLogger("RobotManager")
        self.waiting_for_sensor.set()

    async def send_safe_command(self, command: Command, wait_after: float = 0):
        await self.waiting_for_sensor.wait()
        self.waiting_for_sensor.clear()
        self.serial.send(command)
        if wait_after > 0:
            await asyncio.sleep(wait_after)
        self.waiting_for_sensor.set()

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
        await asyncio.sleep(1)  # Allow time for the connection to stabilize
        while self.running:
            try:
                await asyncio.wait_for(self.ready_event.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                self._logger.warning("Waiting for sensor data timed out, retrying...")
                self.waiting_for_sensor.set()  # op
                
            # Send "SENSOR" command to Arduino to request sensor data
            sensor_request_command = Command(
                ID="",
                command_type=CommandType.SENSOR,
                command=None,
                pause_duration=0,
                duration=0
            )
            self.last_sensor_request_time = time.time()
            self.serial.send(sensor_request_command)
            self.waiting_for_sensor.set()  # Reset waiting for sensor flag
            await asyncio.sleep(self.sensor_request_interval)

    async def _reset_cliff_detected(self):
        """Reset the cliff detected flag after a short duration."""
        await asyncio.sleep(5)  # Wait for 5 seconds before resetting cliff detection to ensure stop
        self.cliff_detected = False
        
    async def _reset_obstacle_detected(self):
        """Reset the obstacle detected flag after a short duration."""
        await asyncio.sleep(5)
        self.obstacle_detected = False

    async def backup(self):
        """Backup the robot for a short duration when an obstacle is detected."""

        await self.send_safe_command(Command.from_joystick(-0.5, 0), wait_after=self.backup_time)
        await self.send_safe_command(Command.stop())  # Stop after backing up
        
    def bytes_to_sensor_data(self, data: bytes):
        """Convert bytes to SensorData model."""

        # Look for start byte (0xAA)
        start_byte = data[0]
        if start_byte != 0xAA:
            self._logger.error(f"Invalid start byte: {hex(start_byte[0])}, searching for 0xAA")
            raise ValueError("Invalid start byte")

        # Unpack the data according to the Arduino's sendSensorData format
        # <B    - start byte (0xAA)
        # B     - distance (uint8_t)
        # h     - ax (int16_t)
        # h     - ay (int16_t)
        # h     - az (int16_t)
        # h     - gx (int16_t)
        # h     - gy (int16_t)
        # h     - gz (int16_t)
        # f     - tempC (float)
        # B     - ir_flags (uint8_t)
        # B     - battery percentage (uint8_t)
        # B     - checksum (uint8_t)
        
        fields = struct.unpack('<BfhhhhhhfBBB', data)
        start, distance, ax, ay, az, gx, gy, gz, temp, ir_flags, battery, received_checksum = fields

        # Calculate checksum (sum of all bytes except start byte and checksum byte)
        calculated_checksum = sum(data[1:-1]) & 0xFF
        valid = calculated_checksum == received_checksum

        if not valid:
            self._logger.error(f"Invalid checksum: calculated={calculated_checksum}, received={received_checksum}")
            raise ValueError("Invalid checksum")
        
        # Extract IR flags
        ir_front = not bool(ir_flags & 0b00000001)
        ir_back = not bool(ir_flags & 0b00000010)
        
        return SensorData(
            ultrasonic={
                "distance": distance
            },
            imu={
                "acceleration_x": ax/16384,  # Convert to g's
                "acceleration_y": ay/16384,  # Convert to g's
                "acceleration_z": az/16384,  # Convert to g's
                "gyroscope_x": gx/131,  # Convert to degrees per second
                "gyroscope_y": gy/131,  # Convert to degrees per second
                "gyroscope_z": gz/131,  # Convert to degrees per second
                "temperature": temp
            },
            ir_front=ir_front,
            ir_back=ir_back,
            battery=battery
        )

    async def handle_obstacle(self, sensor_data: SensorData, current_time: float) -> float:
        """Detect obstacles and trigger backup if needed. Returns processed distance."""
        if not sensor_data.is_obstacle_detected(self.obstacle_threshold) or self.obstacle_detected:
            self.obstacle_detected = False
            return sensor_data.ultrasonic.distance
    
        distance = sensor_data.ultrasonic.distance
        low = distance / self.obstacle_threshold
    
        if distance == -1:  # too far
            avg_distance = sum(self.distance_history) / len(self.distance_history) if self.distance_history else 300
            return avg_distance
        elif distance == -2:  # too close
            avg_distance = sum(self.distance_history) / len(self.distance_history) if self.distance_history else 0
            low = avg_distance / self.obstacle_threshold
        else:
            avg_distance = distance
    
        low = max(0.0, min(low, 1.0))
        high = 1 - low
    
        if current_time - self.last_rumble_time > self.rumble_cooldown:
            await self.socketio.emit('rumble', {"low": low, "high": high, "duration": 1000})
            self.last_rumble_time = current_time
    
        asyncio.create_task(self.backup())
        self.obstacle_detected = True
        asyncio.create_task(self._reset_obstacle_detected())
    
        return avg_distance
                
            
    async def process_sensor_data(self, data: bytes):
        self.waiting_for_sensor.set()
        try:
            sensor_data = self.bytes_to_sensor_data(data)
            if self.sensor_count < 2: # Dont process the first two sensor data packets (UNSTABLE)
                self.sensor_count += 1
                return 
        except Exception as e:
            self._logger.error(f"Error processing sensor data: {e}")
            return

        current_time = time.time()
        sensor_data.ultrasonic.distance = await self.handle_obstacle(sensor_data, current_time)
        self.distance_history.append(sensor_data.ultrasonic.distance)  # Store the distance for history
        
        if len(self.distance_history) >= 10:
            self.distance_history.pop(0)
        # Check for cliff detection
        if sensor_data.check_cliff() and not self.cliff_detected:
            self.cliff_detected = True
            asyncio.create_task(self._reset_cliff_detected())  # Reset cliff detection after 0.5 seconds, basically halting commands
            
            await self.stop_command()

            if current_time - self.last_rumble_time > self.rumble_cooldown:
                await self.socketio.emit(
                    'rumble',
                    {
                        "low": 0.5,
                        "high": 0.5,
                        "duration": 1000,
                    }
                )
                self.last_rumble_time = current_time
        else:
            self.cliff_detected = False

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

        if not self.cliff_detected and self.waiting_for_sensor.is_set() and not self.obstacle_detected:
            await self.send_safe_command(Command.from_joystick(left_y, right_x))
            

    async def _run_command_sequence(self, commands):
        """Run a sequence of commands."""
        try:
            for command in commands.commands:
                await self.socketio.emit('active_command', command.model_dump())
                await self.send_safe_command(command, wait_after=command.duration)
                    
                if command.pause_duration and command.command_type == CommandType.MOTOR:
                    await self.send_safe_command(Command.stop(), wait_after=command.pause_duration)
                    
            await self.send_safe_command(Command.stop())  # Ensure we stop the robot after the command sequence
            await self.socketio.emit('active_command', {
                "ID": ""
            })  # Clear active command
        except Exception as e:
            self._logger.error(f"Error running command sequence: {e}")
            await self.socketio.emit('active_command', {
                "ID": "",
                "error": str(e)
            })
            

    async def handle_query(self, query):
        await self.send_safe_command(
            Command(
                ID="",
                command_type=CommandType.LCD,
                command=LCDCommand(
                    line_1="Thinking...",
                    line_2=""
                ),
                pause_duration=0,
                duration=0
            )
        )
        
        commands = await text_to_command(query)
        command_task = asyncio.create_task(self._run_command_sequence(commands))
        return command_task
    

