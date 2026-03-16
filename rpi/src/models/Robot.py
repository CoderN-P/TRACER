import logging
import threading
import struct
from collections import deque
import asyncio
from . import SerialManager, SensorData, Command, CommandType, LCDCommand, StateEstimator, Mode, ROBOT_CONFIG, MagnetometerData
from .Path import Path
from .PurePursuit import PurePursuit
from ..ai.get_commands import text_to_command


class Robot:
    def __init__(self, serial_manager: SerialManager, socketio):
        self.serial = serial_manager
        self.last_emit_time = 0
        self.last_obstacle_detect_time = 0  # Last time ultrasonic data was processed for obstacle detection
        self.last_cliff_detect_time = 0  # Last time cliff sensors were processed for cliff detection
 
        self.socketio = socketio
        self.cliff_clear = asyncio.Event()
        self.running = False
        self.distance_history = deque(maxlen=10)  # Store last 10 distance readings for smoothing
        
        self.obstacle_clear = asyncio.Event()

        self._logger = logging.getLogger("RobotManager")
        self.motor_lock = asyncio.Lock()
        self.state_estimator = StateEstimator(self._logger)
        
        self.state = Mode.MANUAL
        self.state_lock = asyncio.Lock()  # Lock to protect access to the robot's state (manual, autonomous, stopped)

        self.sensor_lock = threading.Lock()          # shared between serial thread and asyncio
        self.previous_sensor_data = None             # for any processing that needs to compare current and previous sensor data, only accessed within main loop
        self.latest_sensor_data = None               # written by serial thread, read by pose loop
        self.main_loop_task = None 
        
        self.cur_path = None
        
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
        await asyncio.sleep(ROBOT_CONFIG.BACKUP_TIME)  # Wait for half a second before resetting cliff detection to ensure backup completes
        self.cliff_clear.set()
        
    async def _reset_obstacle_clear(self):
        await asyncio.sleep(ROBOT_CONFIG.BACKUP_TIME)  # Wait for backup duration before allowing new obstacle detection
        self.obstacle_clear.set()
        
    async def emergency_stop(self):
        """Immediately stop the robot and clear any pending commands."""
        await self.send_safe_command(Command.estop())
        
        async with self.state_lock:
            self.state = Mode.STOPPED
            
        await self.socketio.emit('emergency_stop', {"status": "success"})
        
        
    async def resume(self):
        """Resume normal operation after an emergency stop."""
        async with self.state_lock:
            self.state = Mode.MANUAL
        await self.send_safe_command(Command.stop())   # clear any stale setpoint
        await self.send_safe_command(Command.enable())
        self.state_estimator.reset()  # Reset state estimator to clear any erroneous state from before the stop
        await self.socketio.emit('resume', {"status": "success"})
            

    async def backup(self):
        """Backup the robot for a short duration when an obstacle is detected."""

        await self.send_safe_command(Command.from_joystick(-0.5, 0), wait_after=self.backup_time)
        await self.send_safe_command(Command.stop())  # Stop after backing up
    
    @staticmethod
    def bytes_to_sensor_data(data: bytes) -> SensorData:
        """Convert bytes to SensorData model."""

        # Look for start byte (0xAA)
        start_byte = data[0]
        if start_byte != 0xAA:
            logger = logging.getLogger("RobotManager")
            logger.error(f"Invalid start byte: {hex(start_byte)}, searching for 0xAA")
            raise ValueError("Invalid start byte")

        # Unpack the data according to the Arduino's sendSensorData format
        # <B    - start byte (0xAA)
        # B     - packet number (uint8_t) 
        # f     - distance (float)
        # h     - ax (int16_t)
        # h     - ay (int16_t)
        # h     - az (int16_t)
        # h     - gx (int16_t)
        # h     - gy (int16_t)
        # h     - gz (int16_t)
        # f     - tempC (float)
        # f     - magnetometer x (float, microtesla)
        # f     - magnetometer y (float, microtesla)
        # f     - magnetometer z (float, microtesla)
        # i     - left encoder ticks (int32_t)
        # i     - right encoder ticks (int32_t)
        # B     - flags (uint8_t) bit 0: front IR, bit 1: back IR, 0 = cliff detected, 1 = no cliff, bit 2: new mag data, bit 3: motors enabled
        # B     - battery percentage (uint8_t)
        # I     - timestamp (uint32_t, microseconds)
        # B     - checksum (uint8_t)
        
        fields = struct.unpack('<BBfhhhhhhffffiiBBIB', data)
        start, packet_num, distance, ax, ay, az, gx, gy, gz, temp, mag_x, mag_y, mag_z, left_encoder_ticks, right_encoder_ticks, flags, battery, timestamp, received_checksum = fields

        # Calculate checksum (sum of all bytes except checksum byte)
        calculated_checksum = sum(data[:-1]) & 0xFF
        valid = calculated_checksum == received_checksum

        if not valid:
            logger = logging.getLogger("RobotManager")
            logger.error(f"Invalid checksum: calculated={calculated_checksum}, received={received_checksum}")
            raise ValueError("Invalid checksum")
        
        # Extract IR flags
        ir_front = not bool(flags & 0b00000001)
        ir_back = not bool(flags & 0b00000010)
        new_mag_data = bool(flags & 0b00000100)
        motors_enabled = bool(flags & 0b00001000)
        
        mag_heading = MagnetometerData.calculate_heading(mag_x, mag_y, mag_z)
        
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
            "magnetometer": {
                "x": mag_x,
                "y": mag_y,
                "z": mag_z,
                "heading": mag_heading,
                "new": new_mag_data
            },
            "left_encoder": left_encoder_ticks,
            "right_encoder": right_encoder_ticks,
            "ir_front": ir_front,
            "ir_back": ir_back,
            "battery": battery,
            "timestamp": timestamp,
            "packet_num": packet_num,
            "motors_enabled": motors_enabled
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
            
        async with self.state_lock:
            cur_state = self.state
            
        if not sensor_data.is_obstacle_detected(ROBOT_CONFIG.OBSTACLE_DETECTED_THRESHOLD) or not self.obstacle_clear.is_set() or cur_state == Mode.STOPPED:
            return avg_distance
    
        await self.socketio.emit('obstacle_detected', {"distance": distance})
    
        # If the distance is below the obstacle avoidance threshold, trigger backup and set obstacle clear flag
        if distance <= ROBOT_CONFIG.OBSTACLE_AVOID_THRESHOLD:
            asyncio.create_task(self.backup())
            self.obstacle_clear.clear()
            asyncio.create_task(self._reset_obstacle_clear())
    
        return avg_distance
    
    
    async def handle_cliff(self, sensor_data: SensorData):
        """Handle cliff detection and stop motors if cliff is detected."""
        async with self.state_lock:
            cur_state = self.state
            
        if not sensor_data.check_cliff() or not self.cliff_clear.is_set() or cur_state == Mode.STOPPED:
            return 
        
        self.cliff_clear.clear()
        asyncio.create_task(self.backup())
        asyncio.create_task(self._reset_cliff_detected())  # Reset cliff detection after 0.5 seconds, basically halting commands

        await self.socketio.emit('cliff_detected', {
            "ir_front": sensor_data.ir_front,
            "ir_back": sensor_data.ir_back
        })
                
            
    async def process_sensor_data(self, data: bytes):
        try:
            new_data = self.bytes_to_sensor_data(data)
            with self.sensor_lock: # Ensure thread-safe access to latest_sensor_data
                self.previous_sensor_data = self.latest_sensor_data
                self.latest_sensor_data = new_data
        except Exception as e:
            self._logger.error(f"Error processing sensor data: {e}")
            return
        
        
    async def send_sensor_update(self, current_time, sensor_data: SensorData):
        dt = 1 / ROBOT_CONFIG.EMIT_SENSOR_FREQ
        if current_time - self.last_emit_time >= dt:
            self.last_emit_time = current_time
            
            async with self.state_lock:
                current_mode = self.state
                
            await self.socketio.emit(
                'sensor_data',
                {
                    "sensors": sensor_data.model_dump(), 
                    "state": self.state_estimator.state.model_dump(),
                    "mode": current_mode.name
                },
            )
    
    async def main_loop(self):
        """Main loop to continuously read sensor data and update state estimator."""
        dt = 1/ROBOT_CONFIG.MAIN_LOOP_FREQ
        
        while self.running:
            start = asyncio.get_event_loop().time()
                    
            with self.sensor_lock:
                sensor_data = self.latest_sensor_data
                prev_data = self.previous_sensor_data
                
            async with self.state_lock:
                if self.state != Mode.STOPPED and sensor_data.motors_enabled == False:
                    self._logger.warning("Motors manually disabled via ESTOP button, switching to STOPPED mode")
                    self.state = Mode.STOPPED
                cur_state = self.state
                
            if not sensor_data:
                elapsed = asyncio.get_event_loop().time() - start
                await asyncio.sleep(max(0, dt - elapsed)) # 100Hz loop
                continue
                
            
            if cur_state != Mode.STOPPED: # Only update state estimator if not stopped
                self.state_estimator.update(sensor_data, prev_data)

            
            if cur_state == Mode.PATH_FOLLOWING:
                if self.cur_path is None:
                    async with self.state_lock:
                        self.state = Mode.MANUAL
                else:
                    exit_path = False
                    if isinstance(self.cur_path, Path): # Quintic Hermite spline path using RAMSETE
                        ready = self.cur_path.is_ready()
                        
                        if ready:
                            if self.cur_path.complete():
                                exit_path = True
                            else:
                                sensor_dt = StateEstimator.calculate_dt(sensor_data.timestamp, prev_data.timestamp)
                                await self.send_safe_command(self.cur_path.get_command(self.state_estimator.state, sensor_dt))
                                
                    elif isinstance(self.cur_path, PurePursuit):
                        # Run pure pursuit
                        command = self.cur_path.calculate_control_command(self.state_estimator.state)
                        
                        if not command:
                            exit_path = True
                        else:
                            await self.send_safe_command(command)
                    else:
                        self._logger.error(f"Unknown path type: {type(self.cur_path)}")
                        exit_path = True
                        
                    if exit_path:
                        async with self.state_lock:
                            self.state = Mode.MANUAL
                        self.cur_path = None
                        await self.send_safe_command(Command.stop())
                        await self.socketio.emit('path_complete', {"status": "success"})
            
            obstacle_dt = 1 / ROBOT_CONFIG.CHECK_OBSTACLE_FREQ
            cliff_dt = 1 / ROBOT_CONFIG.CHECK_CLIFF_FREQ
            
            if (start - self.last_obstacle_detect_time) >= obstacle_dt:
                self.last_obstacle_detect_time = start
                # Will not backup if in STOPPED mode
                sensor_data.ultrasonic.distance = await self.handle_obstacle(sensor_data) ## Run simple smoothing via moving average and handle obstacle detection/backup
                self.distance_history.append(sensor_data.ultrasonic.distance)  # Store the ultrasonic distance for history for smoothing
                
            if (start - self.last_cliff_detect_time) >= cliff_dt:
                self.last_cliff_detect_time = start
                # Will not backup if in STOPPED mode
                await self.handle_cliff(sensor_data)
            
            await self.send_sensor_update(start, sensor_data)
            elapsed = asyncio.get_event_loop().time() - start
            await asyncio.sleep(max(0, dt - elapsed)) # 100Hz loop
    
    async def set_state(self, data):
        """Set the robot's state (manual, path following, stopped)"""
        async with self.state_lock:
            cur_state = self.state
            next_state = Mode[data["state"]]
            
            if next_state == Mode.PATH_FOLLOWING:
                if data["path_type"] == "spline":
                    try:
                        self.cur_path = Path.from_raw(data["path"]["splines"])
                        self.state = Mode.PATH_FOLLOWING
                    except ValueError:
                        self._logger.error("Invalid path data for spline path")
                        self.state = Mode.MANUAL
                elif data["path_type"] == "freehand":
                    self.cur_path = PurePursuit.from_xy_points(data["path"])
                else:
                    self._logger.error(f"Unknown path type: {data['type']}")
                    self.state = Mode.MANUAL
                
            elif next_state == Mode.MANUAL:
                if cur_state == Mode.STOPPED:
                    await self.resume()
                self.state = Mode.MANUAL
            elif next_state == Mode.STOPPED:
                await self.emergency_stop()
        
                
    async def handle_joystick_input(self, data):
        """
        Handle joystick input and send motor commands.
        """
        
        async with self.state_lock:
            cur_state = self.state
            
        if cur_state != Mode.MANUAL:
            return

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
        
        # TODO: Overhaul LLM system to work with distances and velocities instead of duration
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
    

