import logging
import threading
import struct
from collections import deque
from datetime import datetime
import asyncio
from . import SerialManager, SensorData, Command, CommandType, LCDCommand, StateEstimator
from ..ai.get_commands import text_to_command


class Robot:
    def __init__(self, serial_manager: SerialManager, socketio):
        self.serial = serial_manager
        self.last_emit_time = 0
        self.emit_interval = 0.1  # for sensor data, 10Hz update to UI
        self.obstacle_check_interval = 0.05  # Check for obstacles every 50ms (20hz)
        self.cliff_check_interval = 0.05  # Check for cliffs every 50ms (20hz)
        
        self.main_loop_frequency = 100  # Main loop runs at 100Hz
        self.socketio = socketio
        self.cliff_clear = asyncio.Event()
        self.state_estimator = StateEstimator()
        self.running = False
        self.distance_history = deque(maxlen=10)  # Store last 10 distance readings for smoothing
        self.last_obstacle_detect_time = 0  # Last time ultrasonic data was processed for obstacle detection
        self.last_cliff_detect_time = 0  # Last time cliff sensors were processed for cliff detection
        self.obstacle_clear = asyncio.Event()
        self.backup_time = 2  # Amount of time to backup when an obstacle is detected
        self.obstacle_threshold = 20 # Distance threshold for obstacle detection (cm)
        self.obstacle_avoid_threshold = 10 # Distance threshold for obstacle avoidance (cm)
        self._logger = logging.getLogger("RobotManager")
        self.motor_lock = asyncio.Lock()

        self.sensor_lock = threading.Lock()          # shared between serial thread and asyncio
        self.latest_sensor_data = None               # written by serial thread, read by pose loop
        self.main_loop_task = None                   
        
        self.obstacle_clear.set()
        self.cliff_clear.set()

    async def send_safe_command(self, command: Command, wait_after: float = 0):
        async with self.motor_lock:
            self.serial.send(command)
            if wait_after > 0:
                await asyncio.sleep(wait_after)

    async def start(self):
        """Start the robot's background tasks"""
        self.running = True
        self.main_loop_task = asyncio.create_task(self.main_loop())
        self._logger.info("Robot main loop started")

    async def stop(self):
        """Stop the robot's background tasks"""
        self.running = False
        if self.main_loop_task:
            self.main_loop_task.cancel()
            try:
                await self.main_loop_task
            except asyncio.CancelledError:
                pass
        self._logger.info("Robot main loop stopped")

    async def _reset_cliff_detected(self):
        """Reset the cliff clear flag after a short duration."""
        await asyncio.sleep(0.5)  # Wait for half a second before resetting cliff detection to ensure backup completes
        self.cliff_clear.set()
        
    async def _reset_obstacle_clear(self):
        await asyncio.sleep(self.backup_time)  # Wait for backup duration before allowing new obstacle detection
        self.obstacle_clear.set()

    async def backup(self):
        """Backup the robot for a short duration when an obstacle is detected."""

        await self.send_safe_command(Command.from_joystick(-0.5, 0), wait_after=self.backup_time)
        await self.send_safe_command(Command.stop())  # Stop after backing up
        
    def bytes_to_sensor_data(self, data: bytes) -> SensorData:
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
        # I     - timestamp (uint32_t, microseconds)
        # B     - checksum (uint8_t)
        
        fields = struct.unpack('<BfhhhhhhfBBIB', data)
        start, distance, ax, ay, az, gx, gy, gz, temp, ir_flags, battery, timestamp, received_checksum = fields

        # Calculate checksum (sum of all bytes except start byte and checksum byte)
        calculated_checksum = sum(data[1:-1]) & 0xFF
        valid = calculated_checksum == received_checksum

        if not valid:
            self._logger.error(f"Invalid checksum: calculated={calculated_checksum}, received={received_checksum}")
            raise ValueError("Invalid checksum")
        
        # Extract IR flags
        ir_front = not bool(ir_flags & 0b00000001)
        ir_back = not bool(ir_flags & 0b00000010)
        
        data = {
            "ultrasonic": {
                "distance": distance
            },
            "imu": {
                "acceleration_x": ax/16384,  # Convert to g's
                "acceleration_y": ay/16384,  # Convert to g's
                "acceleration_z": az/16384,  # Convert to g's
                "gyroscope_x": gx/131,  # Convert to degrees per second
                "gyroscope_y": gy/131,  # Convert to degrees per second
                "gyroscope_z": gz/131,  # Convert to degrees per second
                "temperature": temp
            },
            "ir_front": ir_front,
            "ir_back": ir_back,
            "battery": battery,
            "timestamp": timestamp
        }
        
        return SensorData.model_validate(data)

    async def handle_obstacle(self, sensor_data: SensorData) -> float:
        """Detect obstacles and trigger backup if needed. Returns processed distance."""
        distance = sensor_data.ultrasonic.distance

        if distance == -1:  # too far
            avg_distance = sum(self.distance_history) / len(self.distance_history) if self.distance_history else 300
            return avg_distance
        elif distance == -2:  # too close
            avg_distance = sum(self.distance_history) / len(self.distance_history) if self.distance_history else 0
        else:
            avg_distance = distance
            
        if not sensor_data.is_obstacle_detected(self.obstacle_threshold) or not self.obstacle_clear.is_set():
            return avg_distance
    
        await self.socketio.emit('obstacle_detected', {"distance": distance})
    
        # If the distance is below the obstacle avoidance threshold, trigger backup and set obstacle clear flag
        if distance <= self.obstacle_avoid_threshold:
            asyncio.create_task(self.backup())
            self.obstacle_clear.clear()
            asyncio.create_task(self._reset_obstacle_clear())
    
        return avg_distance
    
    
    async def handle_cliff(self, sensor_data: SensorData):
        """Handle cliff detection and stop motors if cliff is detected."""
        
        if not sensor_data.check_cliff() or not self.cliff_clear.is_set():
            return 
        
        self.cliff_clear.clear()
        asyncio.create_task(self.backup())
        asyncio.create_task(self._reset_cliff_detected())  # Reset cliff detection after 0.5 seconds, basically halting commands

        await self.send_safe_command(Command.stop())  # Stop motors if cliff is detected
        await self.socketio.emit('cliff_detected', {
            "ir_front": sensor_data.ir_front,
            "ir_back": sensor_data.ir_back
        })
                
            
    async def process_sensor_data(self, data: bytes):
        try:
            with self.sensor_lock: # Ensure thread-safe access to latest_sensor_data
                self.latest_sensor_data = self.bytes_to_sensor_data(data)
        except Exception as e:
            self._logger.error(f"Error processing sensor data: {e}")
            return
        
        
    async def send_sensor_update(self, current_time, sensor_data: SensorData):
        if current_time - self.last_emit_time >= self.emit_interval:
            self.last_emit_time = current_time
            await self.socketio.emit(
                'sensor_data',
                sensor_data.model_dump(),
            )
    
    async def main_loop(self):
        """Main loop to continuously read sensor data and update state estimator."""
        dt = 1/self.main_loop_frequency
        
        while self.running:
            start = asyncio.get_event_loop().time()
            
            with self.sensor_lock:
                sensor_data = self.latest_sensor_data
                
            if not sensor_data:
                elapsed = asyncio.get_event_loop().time() - start
                await asyncio.sleep(max(0, dt - elapsed)) # 100Hz loop
                continue

            self.state_estimator.update(sensor_data)
            
            if (start - self.last_obstacle_detect_time) >= self.obstacle_check_interval:
                self.last_obstacle_detect_time = start
                sensor_data.ultrasonic.distance = await self.handle_obstacle(sensor_data) ## Run simple smoothing via moving average and handle obstacle detection/backup
                self.distance_history.append(sensor_data.ultrasonic.distance)  # Store the ultrasonic distance for history for smoothing
                
            if (start - self.last_cliff_detect_time) >= self.cliff_check_interval:
                self.last_cliff_detect_time = start
                await self.handle_cliff(sensor_data)
            
            await self.send_sensor_update(start, sensor_data)
            elapsed = asyncio.get_event_loop().time() - start
            await asyncio.sleep(max(0, dt - elapsed)) # 100Hz loop

    async def handle_joystick_input(self, data):
        """
        Handle joystick input and send motor commands.
        """

        left_y = data.get('left_y', 0)
        right_x = data.get('right_x', 0)

        if self.cliff_clear.is_set() and self.obstacle_clear.is_set():
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
    

