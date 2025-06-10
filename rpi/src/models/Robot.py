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
        self.waiting_for_sensor = False  # Flag to indicate if we're waiting for sensor data
        self.sensor_request_interval = 0.1  # 10Hz = 0.1 seconds
        self.sensor_request_task = None
        self.running = False
        self.distance_history = []  # Store last 10 distances
        self.sensor_count = 0  # Count of sensor data received
        self.last_sensor_request_time = 0  # Last time sensor data was requested
        self.obstacle_detected = False  # Flag to indicate if an obstacle is detected

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
                if self.waiting_for_sensor and (time.time() - self.last_sensor_request_time >= 1):
                    # If we're waiting for sensor data and 1 second has passed, reset the flag
                    self.waiting_for_sensor = False
                if not self.waiting_for_sensor:
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
                    self.waiting_for_sensor = True  # Set flag to indicate we're waiting for sensor data
                await asyncio.sleep(self.sensor_request_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in sensor request loop: {e}")
                await asyncio.sleep(self.sensor_request_interval)

    async def _reset_cliff_detected(self):
        await asyncio.sleep(5)  # Wait for 5 seconds before resetting cliff detection to ensure stop
        self.cliff_detected = False
        
    async def _reset_obstacle_detected(self):
        await asyncio.sleep(5)
        self.obstacle_detected = False
        
    @staticmethod
    def bytes_to_sensor_data(data: bytes):
        """Convert bytes to SensorData model."""


        # Look for start byte (0xAA)
        start_byte = data[0]
        if start_byte != 0xAA:
            print(f"Invalid start byte: {hex(start_byte[0])}, searching for 0xAA")
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
        # B     - checksum (uint8_t)
        
        fields = struct.unpack('<BfhhhhhhfBB', data)
        start, distance, ax, ay, az, gx, gy, gz, temp, ir_flags, received_checksum = fields

        # Calculate checksum (sum of all bytes except start byte and checksum byte)
        calculated_checksum = sum(data[1:-1]) & 0xFF
        valid = calculated_checksum == received_checksum

        if not valid:
            print(f"Invalid checksum: calculated={calculated_checksum}, received={received_checksum}")
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
        )
    
    async def handle_obstacle(self, sensor_data: SensorData, current_time: float):
        if sensor_data.is_obstacle_detected() and not self.obstacle_detected:
            distance = sensor_data.ultrasonic.distance
            low = distance / 10

            # check if distance is -1 and if so determine if it means too far or too close
            
            if distance == -1: # -1 is used to indicate that the distance is too far away
                # find the average of the last 10 distances
        
                if len(self.distance_history) > 0:
                    avg_distance = sum(self.distance_history) / len(self.distance_history)
                    
                    return avg_distance 
                else:
                    return 300
            elif distance == -2:  # -2 is used to indicate that the distance is too close
                # find the average of the last 10 distances
                if len(self.distance_history) > 0:
                    avg_distance = sum(self.distance_history) / len(self.distance_history)
                    low = avg_distance / 10
                else:
                    avg_distance = 0
            else:
                avg_distance = distance
                
            # clamp low and high to be between 0 and 1
            low = max(0.0, min(low, 1.0))
            high = 1 - low  # Ensure high is always the complement of low

            if current_time - self.last_rumble_time > self.rumble_cooldown:
                await self.socketio.emit(
                    'rumble',
                    {
                        "low": low,
                        "high": high,
                        "duration": 1000,
                    }
                )
                self.last_rumble_time = current_time

            self.waiting_for_sensor = True
            await Command.stop(self.serial)                
            self.obstacle_detected = True  # Set flag to indicate an obstacle is detected
            
            await asyncio.create_task(self._reset_obstacle_detected())
                
            return avg_distance  # Return the average distance for further processing if needed
        else:
            self.obstacle_detected = False
            return sensor_data.ultrasonic.distance  # No obstacle detected, return the current distance
                
            
    async def process_sensor_data(self, data: bytes):
        self.waiting_for_sensor = False  # Reset flag when processing sensor data
        try:
            sensor_data = self.bytes_to_sensor_data(data)
            if self.sensor_count < 2: # Dont process the first two sensor data packets (UNSTABLE)
                self.sensor_count += 1
                return 
        except Exception as e:
            print(f"Error processing sensor data: {e}")
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
            self.waiting_for_sensor = True
            await Command.stop(self.serial)  # Stop motors if cliff is detected

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

        if not self.cliff_detected and not self.waiting_for_sensor and not self.obstacle_detected:
            self.waiting_for_sensor = True  # Set flag to indicate we're waiting for sensor data
            await Command.send_from_joystick(left_y, right_x, self.serial)
            

    async def _run_command_sequence(self, commands):
        try:
            for command in commands.commands:
                self.waiting_for_sensor = True
                self.serial.send(command)
                await self.socketio.emit('active_command', command.model_dump())
                await asyncio.sleep(command.duration)
                if command.pause_duration and command.command_type == CommandType.MOTOR:
                    self.waiting_for_sensor = True
                    await Command.stop(self.serial)
                    await asyncio.sleep(command.pause_duration)
            self.waiting_for_sensor = True 
            await Command.stop(self.serial) # Ensure motors are stopped after command sequence
            await self.socketio.emit('active_command', {
                "ID": ""
            })  # Clear active command
        except Exception as e:
            print(f"Error running command sequence: {e}")
            

    def handle_query(self, query):
        self.serial.send(
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
        
        commands = text_to_command(query)
        command_task = asyncio.create_task(self._run_command_sequence(commands))
        return command_task
