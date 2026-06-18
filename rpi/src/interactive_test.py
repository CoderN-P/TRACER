"""
Interactive Control CLI for differential drive robot.

Features:
- PID tuning with live velocity feedback
- Direct velocity commands (equal or independent per motor)
- Twist commands (linear + angular velocity)
- PWM control for motor testing
- CSV logging of sensor data
- JSON-based gain persistence
"""

import logging
import threading
import time
import json
import csv
from pathlib import Path
from collections import deque
from datetime import datetime

from . import ROBOT_CONFIG
from .models import SerialManager, Robot, Command, CommandType, MotorCommand, MotorPWMCommand, ConfigCommand
from .models.PathFollowing import twist_to_wheel_speeds
# Interval (seconds) between repeated sends while a command is active
SEND_INTERVAL = 0.05
# Display update frequency (Hz)
DISPLAY_HZ = 10
DISPLAY_INTERVAL = 1.0 / DISPLAY_HZ
CONFIG_FIELDS = tuple(ConfigCommand.model_fields.keys())
CONFIG_FIELD_TYPES = {
    key: field.annotation
    for key, field in ConfigCommand.model_fields.items()
}


def _unwrap_optional(annotation):
    return next(
        (arg for arg in getattr(annotation, "__args__", ()) if arg is not type(None)),
        annotation,
    )


def _parse_config_value(key, raw_value):
    expected_type = _unwrap_optional(CONFIG_FIELD_TYPES[key])
    if expected_type is bool:
        value = raw_value.strip().lower()
        if value in {"1", "true", "t", "yes", "y", "on"}:
            return True
        if value in {"0", "false", "f", "no", "n", "off"}:
            return False
        raise ValueError(f"{key} expects a boolean value")

    return expected_type(raw_value)


def _format_config_value(key):
    return getattr(ROBOT_CONFIG, key, None)


def _send_config(serial_manager, updates):
    config_command = ConfigCommand.model_validate(updates)
    serial_manager.send(Command(
        ID="",
        command_type=CommandType.CONFIG,
        command=config_command,
        pause_duration=0,
        duration=0,
    ))

    for key, value in updates.items():
        if hasattr(ROBOT_CONFIG, key):
            setattr(ROBOT_CONFIG, key, value)


class InteractiveTesterState:
    """Encapsulates the state of the interactive tester."""
    
    def __init__(self):
        # PID gains are now part of the embedded config command.
        self.kp_left = ROBOT_CONFIG.P_LEFT
        self.ki_left = ROBOT_CONFIG.I_LEFT
        self.kd_left = ROBOT_CONFIG.D_LEFT
        self.kp_right = ROBOT_CONFIG.P_RIGHT
        self.ki_right = ROBOT_CONFIG.I_RIGHT
        self.kd_right = ROBOT_CONFIG.D_RIGHT
        
        # Target velocity for both wheels (m/s)
        self.target_vel_left = 0.0
        self.target_vel_right = 0.0
        
        # Actual velocity tracking
        self.actual_vel_left = 0.0
        self.actual_vel_right = 0.0
        self.error_left = 0.0
        self.error_right = 0.0
        
        # Encoder tracking for velocity calculation
        self.last_encoder_left = 0
        self.last_encoder_right = 0
        self.last_timestamp = None
        
        # Session statistics (reset at start of each command)
        self.session_packets = 0
        self.session_total_ticks_left = 0
        self.session_total_ticks_right = 0
        
        # Logging
        self.csv_file = None
        self.csv_writer = None
        self.logging_enabled = False
        
        # Display history for smoothing
        self.vel_history_left = deque(maxlen=10)
        self.vel_history_right = deque(maxlen=10)
    
    def update_velocity_from_encoder(self, sensor_data, current_time):
        """Calculate actual velocity from encoder deltas."""
        if self.last_timestamp is None:
            self.last_timestamp = current_time
            self.last_encoder_left = sensor_data.left_encoder
            self.last_encoder_right = sensor_data.right_encoder
            self.session_packets += 1
            self.session_total_ticks_left += sensor_data.left_encoder
            self.session_total_ticks_right += sensor_data.right_encoder
            return
        
        dt = current_time - self.last_timestamp
        if dt <= 0:
            return
        
        # Track total encoder ticks
        self.session_packets += 1
        self.session_total_ticks_left += sensor_data.left_encoder
        self.session_total_ticks_right += sensor_data.right_encoder
        
        # Calculate distance traveled
        delta_left = sensor_data.left_encoder * (
            ROBOT_CONFIG.METERS_PER_TICK_LEFT_POS
            if sensor_data.left_encoder >= 0
            else ROBOT_CONFIG.METERS_PER_TICK_LEFT_NEG
        )
        delta_right = sensor_data.right_encoder * (
            ROBOT_CONFIG.METERS_PER_TICK_RIGHT_POS
            if sensor_data.right_encoder >= 0
            else ROBOT_CONFIG.METERS_PER_TICK_RIGHT_NEG
        )
        
        # Calculate velocity (m/s)
        vel_left = delta_left / dt
        vel_right = delta_right / dt
        
        # Store in history for averaging
        self.vel_history_left.append(vel_left)
        self.vel_history_right.append(vel_right)
        
        # Smooth velocity readings
        self.actual_vel_left = sum(self.vel_history_left) / len(self.vel_history_left)
        self.actual_vel_right = sum(self.vel_history_right) / len(self.vel_history_right)
        
        # Calculate error
        self.error_left = self.target_vel_left - self.actual_vel_left
        self.error_right = self.target_vel_right - self.actual_vel_right
        
        # Update timestamp for next iteration
        self.last_timestamp = current_time
    
    def start_logging(self, filename):
        """Start CSV logging to the specified file."""
        try:
            # Ensure calibration_files/pid directory exists
            log_dir = Path(__file__).parent.parent.parent / "calibration_files" / "pid"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Construct full path
            filepath = log_dir / filename
            
            self.csv_file = open(filepath, 'w', newline='')
            self.csv_writer = csv.writer(self.csv_file)
            self.csv_writer.writerow([
                'timestamp', 
                'target_l', 'actual_l', 'error_l',
                'target_r', 'actual_r', 'error_r'
            ])
            self.logging_enabled = True
            print(f"Logging started: {filepath}")
        except IOError as e:
            print(f"Error opening log file: {e}")
    
    def stop_logging(self):
        """Stop CSV logging."""
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None
            self.csv_writer = None
            self.logging_enabled = False
            print("Logging stopped")
    
    def log_data(self):
        """Write current state to CSV log."""
        if not self.logging_enabled or not self.csv_writer:
            return
        
        try:
            self.csv_writer.writerow([
                datetime.now().isoformat(),
                f"{self.target_vel_left:.4f}",
                f"{self.actual_vel_left:.4f}",
                f"{self.error_left:.4f}",
                f"{self.target_vel_right:.4f}",
                f"{self.actual_vel_right:.4f}",
                f"{self.error_right:.4f}"
            ])
            self.csv_file.flush()
        except Exception as e:
            print(f"Error writing to log: {e}")
    
    def save_gains_to_file(self, filename):
        """Save current PID gains to JSON file."""
        try:
            # Ensure calibration_files/pid directory exists
            gains_dir = Path(__file__).parent.parent.parent / "calibration_files" / "pid"
            gains_dir.mkdir(parents=True, exist_ok=True)
            
            # Construct full path
            filepath = gains_dir / filename
            
            gains = {
                'P_LEFT': self.kp_left,
                'I_LEFT': self.ki_left,
                'D_LEFT': self.kd_left,
                'P_RIGHT': self.kp_right,
                'I_RIGHT': self.ki_right,
                'D_RIGHT': self.kd_right,
                'timestamp': datetime.now().isoformat()
            }
            with open(filepath, 'w') as f:
                json.dump(gains, f, indent=2)
            print(f"Gains saved to {filepath}")
        except IOError as e:
            print(f"Error saving gains: {e}")
    
    def load_gains_from_file(self, filename):
        """Load PID gains from JSON file."""
        try:
            # Try to load from calibration_files/pid first
            gains_dir = Path(__file__).parent.parent.parent / "calibration_files" / "pid"
            filepath = gains_dir / filename
            
            # If not found in calibration dir, try current directory or absolute path
            if not filepath.exists():
                filepath = Path(filename)
            
            with open(filepath, 'r') as f:
                gains = json.load(f)
            self.kp_left = gains.get('P_LEFT', gains.get('kp_left', self.kp_left))
            self.ki_left = gains.get('I_LEFT', gains.get('ki_left', self.ki_left))
            self.kd_left = gains.get('D_LEFT', gains.get('kd_left', self.kd_left))
            self.kp_right = gains.get('P_RIGHT', gains.get('kp_right', self.kp_right))
            self.ki_right = gains.get('I_RIGHT', gains.get('ki_right', self.ki_right))
            self.kd_right = gains.get('D_RIGHT', gains.get('kd_right', self.kd_right))
            print(f"Gains loaded from {filepath}")
            self.print_gains()
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading gains: {e}")
    
    def print_gains(self):
        """Print current PID gains."""
        print(f"\n[PID] kP_l={self.kp_left:.2f} kI_l={self.ki_left:.2f} kD_l={self.kd_left:.2f} " +
              f"kP_r={self.kp_right:.2f} kI_r={self.ki_right:.2f} kD_r={self.kd_right:.2f}\n")
    
    def reset_session_stats(self):
        """Reset session statistics for a new command."""
        self.session_packets = 0
        self.session_total_ticks_left = 0
        self.session_total_ticks_right = 0
        self.last_timestamp = None
    
    def report_session_stats(self, duration):
        """Print session statistics at the end of a command."""
        # Calculate distances
        distance_left = self.session_total_ticks_left * (
            ROBOT_CONFIG.METERS_PER_TICK_LEFT_POS
            if self.session_total_ticks_left >= 0
            else ROBOT_CONFIG.METERS_PER_TICK_LEFT_NEG
        )
        distance_right = self.session_total_ticks_right * (
            ROBOT_CONFIG.METERS_PER_TICK_RIGHT_POS
            if self.session_total_ticks_right >= 0
            else ROBOT_CONFIG.METERS_PER_TICK_RIGHT_NEG
        )
        avg_distance = (distance_left + distance_right) / 2.0
        
        print(f"\n{'='*80}")
        print(f"Session Report ({duration:.1f}s)")
        print(f"{'='*80}")
        print(f"Total Packets:        {self.session_packets}")
        print(f"Left Encoder Ticks:   {self.session_total_ticks_left}")
        print(f"Right Encoder Ticks:  {self.session_total_ticks_right}")
        print(f"Left Distance:        {distance_left:.4f} m ({distance_left*100:.2f} cm)")
        print(f"Right Distance:       {distance_right:.4f} m ({distance_right*100:.2f} cm)")
        print(f"Average Distance:     {avg_distance:.4f} m ({avg_distance*100:.2f} cm)")
        print(f"{'='*80}\n")


def _print_live_display(state: InteractiveTesterState):
    """Print the live display line."""
    status = (f"[PID] kP_l={state.kp_left:.2f} kI_l={state.ki_left:.2f} kD_l={state.kd_left:.2f} " +
              f"kP_r={state.kp_right:.2f} kI_r={state.ki_right:.2f} kD_r={state.kd_right:.2f} | " +
              f"tgt_L={state.target_vel_left:.2f} tgt_R={state.target_vel_right:.2f} | " +
              f"L: act={state.actual_vel_left:.3f} err={state.error_left:+.3f} | " +
              f"R: act={state.actual_vel_right:.3f} err={state.error_right:+.3f}")
    print(status.ljust(140)[:140], end='\n')


def interactive_test(port=None):
    """
    Interactive control CLI for differential drive robot.
    
    Commands:
    - pid <kp> <ki> <kd>              — set same embedded PID gains for both wheels
    - pid <kpl> <kil> <kdl> <kpr> <kir> <kdr> — set independent embedded PID gains
    - config                          — list editable embedded config constants
    - config get <key>                — show one embedded config constant
    - config set <key> <value>        — update one embedded config constant
    - vel <speed> [duration]          — command equal velocity to both motors (m/s, default 10s)
    - vel <left_speed> <right_speed> <duration> — command different speeds per motor (m/s)
    - twist <linear> <angular> [duration] — command using linear and angular velocity (default 10s)
    - pwm <pwm> [duration]            — command equal PWM to both motors (default 1s)
    - pwm <pwm_left> <pwm_right> [duration] — command different PWM per motor (default 1s)
    - step <speed> [duration]         — step response test (default 3s)
    - stop                            — stop motors immediately
    - log <filename>                  — toggle CSV logging to file
    - save <filename>                 — save current gains to JSON
    - load <filename>                 — load gains from JSON
    - gains                           — print current gains
    - quit                            — stop motors and exit
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    logger = logging.getLogger(__name__)
    
    serial_port = port if port else SerialManager.find_port()
    if not serial_port:
        logger.error("No serial port found. Please connect the robot.")
        return
    else:
        logger.info("Port: " + serial_port)
    
    # Initialize state
    state = InteractiveTesterState()
    active_command = None
    command_end_time = None
    command_start_time = None
    command_duration = 0
    display_last_time = time.time()
    run_active = False
    coasting_down = False  # Track if we're in deceleration phase
    coast_start_time = None
    coast_stopped_time = None
    
    lock = threading.Lock()
    
    def sensor_callback(data):
        """Callback for sensor data updates."""
        nonlocal run_active
        if not data:
            return
        
        sensor_data = Robot.bytes_to_sensor_data(data)
        with lock:
            if run_active:
                state.update_velocity_from_encoder(sensor_data, time.time())
    
    serial_manager = SerialManager(serial_port, 921600)
    serial_manager.start_read(callback=sensor_callback)
    
    print("\n" + "="*100)
    print("Interactive Control CLI - Differential Drive Robot")
    print("="*100)
    print("Commands: pid, config, vel, twist, pwm, step, stop, log, save, load, gains, quit")
    print("Type 'help' for detailed command information.")
    print("="*100 + "\n")
    
    try:
        while True:
            # If active command is running, show live display and re-send
            if active_command is not None:
                now = time.time()
                
                # Check if commanded duration has elapsed
                if not coasting_down and command_end_time is not None and now >= command_end_time:
                    # Duration reached - start coast-down phase
                    serial_manager.send(Command.stop())
                    coasting_down = True
                    coast_start_time = now
                    coast_stopped_time = None
                
                # If coasting down, check if velocity has reached zero
                if coasting_down:
                    velocity_threshold = 0.005  # m/s
                    with lock:
                        left_vel = abs(state.actual_vel_left)
                        right_vel = abs(state.actual_vel_right)
                    
                    if left_vel < velocity_threshold and right_vel < velocity_threshold:
                        # Velocity is near zero
                        if coast_stopped_time is None:
                            coast_stopped_time = now
                        # If been zero for 0.2s, we're done
                        elif now - coast_stopped_time > 0.2 or now - coast_start_time > 3.0:
                            # Robot has fully stopped
                            actual_duration = now - command_start_time if command_start_time else command_duration
                            
                            with lock:
                                state.target_vel_left = 0.0
                                state.target_vel_right = 0.0
                                state.report_session_stats(actual_duration)
                                run_active = False
                            
                            active_command = None
                            coasting_down = False
                            command_end_time = None
                            command_start_time = None
                            coast_start_time = None
                            coast_stopped_time = None
                            print()
                            continue
                    else:
                        # Still moving - reset the stopped timer
                        coast_stopped_time = None
                
                # Show live display
                if now - display_last_time >= DISPLAY_INTERVAL:
                    with lock:
                        _print_live_display(state)
                        if state.logging_enabled:
                            state.log_data()
                    display_last_time = now
                
                # Resend the current command while active, or keep sending stop while coasting
                serial_manager.send(Command.stop() if coasting_down else active_command)
                time.sleep(SEND_INTERVAL)
                continue
            
            # No active command - prompt for input (blocking)
            try:
                raw = input("ctrl> ").strip()
            except KeyboardInterrupt:
                raise
            except:
                time.sleep(0.01)
                continue
            
            if not raw:
                continue
            
            # Parse command
            parts = raw.split()
            cmd_name = parts[0].lower()
            args = parts[1:]
            
            if cmd_name in {"q", "quit", "exit"}:
                break
            
            elif cmd_name == "help":
                print("\nAvailable Commands:")
                print("  pid <kp> <ki> <kd>")
                print("      - Set same embedded PID gains for both wheels")
                print("  pid <kpl> <kil> <kdl> <kpr> <kir> <kdr>")
                print("      - Set independent embedded PID gains for each wheel")
                print("  config")
                print("      - List all ConfigCommand constants and current values")
                print("  config get <key>")
                print("      - Show one ConfigCommand constant")
                print("  config set <key> <value>")
                print("      - Update one ConfigCommand constant (booleans accept true/false, on/off, 1/0)")
                print("  vel <speed> [duration]")
                print("      - Command equal velocity to both motors (m/s, default 10s)")
                print("  vel <left_speed> <right_speed> <duration>")
                print("      - Command different speeds per motor (m/s)")
                print("  twist <linear> <angular> [duration]")
                print("      - Command using linear (m/s) and angular (rad/s) velocity (default 10s)")
                print("  pwm <pwm> [duration]")
                print("      - Command equal PWM to both motors [-1.0, 1.0] (default 1s)")
                print("  pwm <pwm_left> <pwm_right> [duration]")
                print("      - Command different PWM per motor (default 1s)")
                print("  step <speed> [duration]")
                print("      - Step response test: 0→speed m/s (default 3s)")
                print("  stop")
                print("      - Stop motors immediately")
                print("  log <filename>")
                print("      - Toggle CSV logging to file")
                print("  save <filename>")
                print("      - Save current gains to JSON")
                print("  load <filename>")
                print("      - Load gains from JSON")
                print("  gains")
                print("      - Print current PID gains")
                print("  quit")
                print("      - Exit\n")
            
            elif cmd_name == "pid":
                if len(args) == 3:
                    try:
                        kp = float(args[0])
                        ki = float(args[1])
                        kd = float(args[2])
                        with lock:
                            state.kp_left = kp
                            state.ki_left = ki
                            state.kd_left = kd
                            state.kp_right = kp
                            state.ki_right = ki
                            state.kd_right = kd
                        _send_config(serial_manager, {
                            "P_LEFT": state.kp_left,
                            "I_LEFT": state.ki_left,
                            "D_LEFT": state.kd_left,
                            "P_RIGHT": state.kp_right,
                            "I_RIGHT": state.ki_right,
                            "D_RIGHT": state.kd_right,
                        })
                        print(f"✓ PID gains set (both wheels): kP={kp:.2f} kI={ki:.2f} kD={kd:.2f}\n")
                    except ValueError:
                        print("✗ Invalid number format. Example: pid 1.5 0.0 0.2\n")
                
                elif len(args) == 6:
                    try:
                        kpl, kil, kdl, kpr, kir, kdr = map(float, args)
                        with lock:
                            state.kp_left = kpl
                            state.ki_left = kil
                            state.kd_left = kdl
                            state.kp_right = kpr
                            state.ki_right = kir
                            state.kd_right = kdr
                        _send_config(serial_manager, {
                            "P_LEFT": state.kp_left,
                            "I_LEFT": state.ki_left,
                            "D_LEFT": state.kd_left,
                            "P_RIGHT": state.kp_right,
                            "I_RIGHT": state.ki_right,
                            "D_RIGHT": state.kd_right,
                        })
                        print(f"✓ PID gains set independently:")
                        print(f"  Left:  kP={kpl:.2f} kI={kil:.2f} kD={kdl:.2f}")
                        print(f"  Right: kP={kpr:.2f} kI={kir:.2f} kD={kdr:.2f}\n")
                    except ValueError:
                        print("✗ Invalid number format. Example: pid 1.5 0.0 0.2 1.8 0.0 0.25\n")
                else:
                    print("✗ PID requires either 3 or 6 arguments\n")

            elif cmd_name == "config":
                if not args:
                    print("\nConfigCommand constants:")
                    for key in CONFIG_FIELDS:
                        print(f"  {key:<24} {_format_config_value(key)}")
                    print("\nUse: config set <key> <value>\n")
                    continue

                action = args[0].lower()
                if action == "get":
                    if len(args) != 2:
                        print("✗ config get requires a key\n")
                        continue
                    key = args[1].upper()
                    if key not in CONFIG_FIELDS:
                        print(f"✗ Unknown ConfigCommand key: {key}\n")
                        continue
                    print(f"{key} = {_format_config_value(key)}\n")
                    continue

                if action == "set":
                    if len(args) != 3:
                        print("✗ config set requires a key and value\n")
                        continue
                    key = args[1].upper()
                    raw_value = args[2]
                elif len(args) == 2:
                    key = args[0].upper()
                    raw_value = args[1]
                else:
                    print("✗ config usage: config, config get <key>, config set <key> <value>\n")
                    continue

                if key not in CONFIG_FIELDS:
                    print(f"✗ Unknown ConfigCommand key: {key}\n")
                    continue

                try:
                    value = _parse_config_value(key, raw_value)
                    _send_config(serial_manager, {key: value})
                    with lock:
                        if key == "P_LEFT":
                            state.kp_left = value
                        elif key == "I_LEFT":
                            state.ki_left = value
                        elif key == "D_LEFT":
                            state.kd_left = value
                        elif key == "P_RIGHT":
                            state.kp_right = value
                        elif key == "I_RIGHT":
                            state.ki_right = value
                        elif key == "D_RIGHT":
                            state.kd_right = value
                    print(f"✓ {key} set to {value}\n")
                except ValueError as exc:
                    print(f"✗ {exc}\n")
            
            elif cmd_name == "vel":
                if len(args) < 1 or len(args) > 3:
                    print("✗ vel requires 1-3 arguments: speed [duration] or left_speed right_speed duration\n")
                    continue
                
                try:
                    if len(args) == 1:
                        # vel <speed> [duration]
                        speed = float(args[0])
                        duration = 10.0  # Default 10 seconds
                        
                        if not (-ROBOT_CONFIG.MAX_LINEAR_VEL_NEG <= speed <= ROBOT_CONFIG.MAX_LINEAR_VEL_POS):
                            print(f"✗ Speed must be between -{ROBOT_CONFIG.MAX_LINEAR_VEL_NEG:.2f} and {ROBOT_CONFIG.MAX_LINEAR_VEL_POS:.2f} m/s\n")
                            continue
                        
                        with lock:
                            state.target_vel_left = speed
                            state.target_vel_right = speed
                            state.reset_session_stats()
                            run_active = True
                        
                        active_command = Command(
                            ID="",
                            command_type=CommandType.MOTOR,
                            command=MotorCommand(left_motor=speed, right_motor=speed),
                            duration=0,
                            pause_duration=0
                        )
                        command_start_time = time.time()
                        command_duration = duration
                        command_end_time = command_start_time + duration
                        coasting_down = False
                        print(f"✓ Velocity command: {speed:.2f} m/s (both motors) for {duration:.1f}s")
                        print("Live display:\n")
                    
                    elif len(args) == 2:
                        # vel <speed> <duration>
                        speed = float(args[0])
                        duration = float(args[1])
                        
                        if not (-ROBOT_CONFIG.MAX_LINEAR_VEL_NEG <= speed <= ROBOT_CONFIG.MAX_LINEAR_VEL_POS):
                            print(f"✗ Speed must be between -{ROBOT_CONFIG.MAX_LINEAR_VEL_NEG:.2f} and {ROBOT_CONFIG.MAX_LINEAR_VEL_POS:.2f} m/s\n")
                            continue
                        
                        if duration <= 0:
                            print("✗ Duration must be > 0 seconds\n")
                            continue
                        
                        with lock:
                            state.target_vel_left = speed
                            state.target_vel_right = speed
                            state.reset_session_stats()
                            run_active = True
                        
                        active_command = Command(
                            ID="",
                            command_type=CommandType.MOTOR,
                            command=MotorCommand(left_motor=speed, right_motor=speed),
                            duration=0,
                            pause_duration=0
                        )
                        command_start_time = time.time()
                        command_duration = duration
                        command_end_time = command_start_time + duration
                        coasting_down = False
                        print(f"✓ Velocity command: {speed:.2f} m/s (both motors) for {duration:.1f}s")
                        print("Live display:\n")
                    
                    elif len(args) == 3:
                        # vel <left_speed> <right_speed> <duration>
                        left_speed = float(args[0])
                        right_speed = float(args[1])
                        duration = float(args[2])
                        
                        if not (-ROBOT_CONFIG.MAX_LINEAR_VEL_NEG <= left_speed <= ROBOT_CONFIG.MAX_LINEAR_VEL_POS):
                            print(f"✗ Left speed must be between -{ROBOT_CONFIG.MAX_LINEAR_VEL_NEG:.2f} and {ROBOT_CONFIG.MAX_LINEAR_VEL_PIS:.2f} m/s\n")
                            continue
                        
                        if not (-ROBOT_CONFIG.MAX_LINEAR_VEL_NEG <= right_speed <= ROBOT_CONFIG.MAX_LINEAR_VEL_POS):
                            print(f"✗ Right speed must be between -{ROBOT_CONFIG.MAX_LINEAR_VEL_NEG:.2f} and {ROBOT_CONFIG.MAX_LINEAR_VEL_POS:.2f} m/s\n")
                            continue
                        
                        if duration <= 0:
                            print("✗ Duration must be > 0 seconds\n")
                            continue
                        
                        with lock:
                            state.target_vel_left = left_speed
                            state.target_vel_right = right_speed
                            state.reset_session_stats()
                            run_active = True
                        
                        active_command = Command(
                            ID="",
                            command_type=CommandType.MOTOR,
                            command=MotorCommand(left_motor=left_speed, right_motor=right_speed),
                            duration=0,
                            pause_duration=0
                        )
                        command_start_time = time.time()
                        command_duration = duration
                        command_end_time = command_start_time + duration
                        coasting_down = False
                        print(f"✓ Velocity command: L={left_speed:.2f} m/s, R={right_speed:.2f} m/s for {duration:.1f}s")
                        print("Live display:\n")
                
                except ValueError:
                    print("✗ Invalid number format\n")
            
            elif cmd_name == "twist":
                if len(args) < 2 or len(args) > 3:
                    print("✗ twist requires 2-3 arguments: linear angular [duration]\n")
                    continue
                
                try:
                    linear = float(args[0])
                    angular = float(args[1])
                    duration = float(args[2]) if len(args) > 2 else 10.0  # Default 10 seconds
                    
                    if duration <= 0:
                        print("✗ Duration must be > 0 seconds\n")
                        continue
                    
                    # Use twist_to_wheel_speeds to convert
                    left_speed, right_speed = twist_to_wheel_speeds(linear, angular)
                    
                    # Clamp to max speeds
                    left_speed = max(-ROBOT_CONFIG.MAX_LINEAR_VEL_NEG, min(ROBOT_CONFIG.MAX_LINEAR_VEL_POS, left_speed))
                    right_speed = max(-ROBOT_CONFIG.MAX_LINEAR_VEL_NEG, min(ROBOT_CONFIG.MAX_LINEAR_VEL_POS, right_speed))
                    
                    with lock:
                        state.target_vel_left = left_speed
                        state.target_vel_right = right_speed
                        state.reset_session_stats()
                        run_active = True
                    
                    active_command = Command(
                        ID="",
                        command_type=CommandType.MOTOR,
                        command=MotorCommand(left_motor=left_speed, right_motor=right_speed),
                        duration=0,
                        pause_duration=0
                    )
                    command_start_time = time.time()
                    command_duration = duration
                    command_end_time = command_start_time + duration
                    coasting_down = False
                    print(f"✓ Twist command: linear={linear:.2f} m/s, angular={angular:.2f} rad/s → L={left_speed:.2f}, R={right_speed:.2f} m/s for {duration:.1f}s")
                    print("Live display:\n")
                
                except ValueError:
                    print("✗ Invalid number format. Example: twist 0.2 0.5 5.0\n")
            
            elif cmd_name == "pwm":
                if len(args) < 1 or len(args) > 3:
                    print("✗ pwm requires 1-3 arguments: pwm [duration] or pwm_left pwm_right [duration]\n")
                    continue
                
                try:
                    if len(args) == 1:
                        # pwm <pwm> [duration]
                        pwm = float(args[0])
                        duration = 1.0  # Default 1 second
                        
                        if not (-1.0 <= pwm <= 1.0):
                            print("✗ PWM must be between -1.0 and 1.0\n")
                            continue
                        
                        with lock:
                            state.target_vel_left = 0.0  # PWM mode doesn't have velocity targets
                            state.target_vel_right = 0.0
                            state.reset_session_stats()
                            run_active = True
                        
                        active_command = Command(
                            ID="",
                            command_type=CommandType.PWM,
                            command=MotorPWMCommand(left_motor=pwm, right_motor=pwm),
                            duration=0,
                            pause_duration=0
                        )
                        command_start_time = time.time()
                        command_duration = duration
                        command_end_time = command_start_time + duration
                        coasting_down = False
                        print(f"✓ PWM command: {pwm:.3f} (both motors) for {duration:.1f}s")
                        print("Live display:\n")
                    
                    elif len(args) == 2:
                        # Could be: pwm <pwm> <duration> OR pwm <pwm_left> <pwm_right>
                        val1 = float(args[0])
                        val2 = float(args[1])
                        
                        # Check if both are PWM values (between -1 and 1)
                        if -1.0 <= val1 <= 1.0 and -1.0 <= val2 <= 1.0:
                            # Ambiguous case: interpret as two PWM values with default 1s duration
                            pwm_left = val1
                            pwm_right = val2
                            duration = 1.0
                            
                            with lock:
                                state.target_vel_left = 0.0
                                state.target_vel_right = 0.0
                                state.reset_session_stats()
                                run_active = True
                            
                            active_command = Command(
                                ID="",
                                command_type=CommandType.PWM,
                                command=MotorPWMCommand(left_motor=pwm_left, right_motor=pwm_right),
                                duration=0,
                                pause_duration=0
                            )
                            command_start_time = time.time()
                            command_duration = duration
                            command_end_time = command_start_time + duration
                            coasting_down = False
                            print(f"✓ PWM command: L={pwm_left:.3f}, R={pwm_right:.3f} for {duration:.1f}s")
                            print("Live display:\n")
                        else:
                            # Treat as pwm <pwm> <duration>
                            pwm = val1
                            duration = val2
                            
                            if not (-1.0 <= pwm <= 1.0):
                                print("✗ PWM must be between -1.0 and 1.0\n")
                                continue
                            
                            if duration <= 0:
                                print("✗ Duration must be > 0 seconds\n")
                                continue
                            
                            with lock:
                                state.target_vel_left = 0.0
                                state.target_vel_right = 0.0
                                state.reset_session_stats()
                                run_active = True
                            
                            active_command = Command(
                                ID="",
                                command_type=CommandType.PWM,
                                command=MotorPWMCommand(left_motor=pwm, right_motor=pwm),
                                duration=0,
                                pause_duration=0
                            )
                            command_start_time = time.time()
                            command_duration = duration
                            command_end_time = command_start_time + duration
                            coasting_down = False
                            print(f"✓ PWM command: {pwm:.3f} (both motors) for {duration:.1f}s")
                            print("Live display:\n")
                    
                    elif len(args) == 3:
                        # pwm <pwm_left> <pwm_right> <duration>
                        pwm_left = float(args[0])
                        pwm_right = float(args[1])
                        duration = float(args[2])
                        
                        if not (-1.0 <= pwm_left <= 1.0):
                            print("✗ Left PWM must be between -1.0 and 1.0\n")
                            continue
                        
                        if not (-1.0 <= pwm_right <= 1.0):
                            print("✗ Right PWM must be between -1.0 and 1.0\n")
                            continue
                        
                        if duration <= 0:
                            print("✗ Duration must be > 0 seconds\n")
                            continue
                        
                        with lock:
                            state.target_vel_left = 0.0
                            state.target_vel_right = 0.0
                            state.reset_session_stats()
                            run_active = True
                        
                        active_command = Command(
                            ID="",
                            command_type=CommandType.PWM,
                            command=MotorPWMCommand(left_motor=pwm_left, right_motor=pwm_right),
                            duration=0,
                            pause_duration=0
                        )
                        command_start_time = time.time()
                        command_duration = duration
                        command_end_time = command_start_time + duration
                        coasting_down = False
                        print(f"✓ PWM command: L={pwm_left:.3f}, R={pwm_right:.3f} for {duration:.1f}s")
                        print("Live display:\n")
                
                except ValueError:
                    print("✗ Invalid number format\n")
            
            elif cmd_name == "step":
                if len(args) < 1 or len(args) > 2:
                    print("✗ step requires 1-2 arguments: speed [duration]\n")
                    continue
                
                try:
                    speed = float(args[0])
                    duration = float(args[1]) if len(args) > 1 else 3.0  # Default 3 seconds
                    
                    if not (0 < speed <= ROBOT_CONFIG.MAX_LINEAR_VEL_POS):
                        print(f"✗ Speed must be between 0 and {ROBOT_CONFIG.MAX_LINEAR_VEL_POS:.2f} m/s\n")
                        continue
                    
                    if duration <= 0:
                        print("✗ Duration must be > 0 seconds\n")
                        continue
                    
                    with lock:
                        state.target_vel_left = speed
                        state.target_vel_right = speed
                        state.reset_session_stats()
                        run_active = True
                    
                    active_command = Command(
                        ID="",
                        command_type=CommandType.MOTOR,
                        command=MotorCommand(left_motor=speed, right_motor=speed),
                        duration=0,
                        pause_duration=0
                    )
                    command_start_time = time.time()
                    command_duration = duration
                    command_end_time = command_start_time + duration
                    coasting_down = False
                    print(f"✓ Step response test: 0→{speed:.2f} m/s for {duration:.1f}s")
                    print("Live display:\n")
                except ValueError:
                    print("✗ Invalid speed or duration value\n")
            
            elif cmd_name == "stop":
                serial_manager.send(Command.stop())
                active_command = None
                command_end_time = None
                command_start_time = None
                with lock:
                    state.target_vel_left = 0.0
                    state.target_vel_right = 0.0
                    run_active = False
                print("✓ Motors stopped\n")
            
            elif cmd_name == "log":
                if len(args) != 1:
                    print("✗ log requires a filename\n")
                    continue
                
                if state.logging_enabled:
                    state.stop_logging()
                else:
                    state.start_logging(args[0])
                print()
            
            elif cmd_name == "save":
                if len(args) != 1:
                    print("✗ save requires a filename\n")
                    continue
                state.save_gains_to_file(args[0])
                print()
            
            elif cmd_name == "load":
                if len(args) != 1:
                    print("✗ load requires a filename\n")
                    continue
                state.load_gains_from_file(args[0])
                print()
            
            elif cmd_name == "gains":
                with lock:
                    state.print_gains()
            
            else:
                print(f"✗ Unknown command: {cmd_name}. Type 'help' for available commands.\n")
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    finally:
        # Cleanup
        serial_manager.send(Command.stop())
        if state.logging_enabled:
            state.stop_logging()
        serial_manager.stop()
        print("Serial connection closed. Goodbye.")
