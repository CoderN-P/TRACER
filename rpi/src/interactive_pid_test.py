"""
Interactive PID tuning CLI for differential drive robot velocity control.

Features:
- Sends PID gain updates via binary protocol
- Displays live velocity tracking at 10Hz
- Logs data to CSV for post-analysis
- Supports JSON-based gain persistence
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
from .models import SerialManager, Robot, Command, CommandType, MotorCommand, PIDCommand

# Interval (seconds) between repeated sends while a command is active
SEND_INTERVAL = 0.05
# Display update frequency (Hz)
DISPLAY_HZ = 10
DISPLAY_INTERVAL = 1.0 / DISPLAY_HZ


class PIDTunerState:
    """Encapsulates the state of the PID tuner."""
    
    def __init__(self):
        # PID gains (initialize with reasonable defaults)
        self.kp_left = 1.5
        self.ki_left = 0.0
        self.kd_left = 0.2
        self.kp_right = 1.8
        self.ki_right = 0.0
        self.kd_right = 0.25
        
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
        delta_left = sensor_data.left_encoder * ROBOT_CONFIG.METERS_PER_TICK_LEFT
        delta_right = sensor_data.right_encoder * ROBOT_CONFIG.METERS_PER_TICK_RIGHT
        
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
            self.csv_file = open(filename, 'w', newline='')
            self.csv_writer = csv.writer(self.csv_file)
            self.csv_writer.writerow([
                'timestamp', 
                'target_l', 'actual_l', 'error_l',
                'target_r', 'actual_r', 'error_r'
            ])
            self.logging_enabled = True
            print(f"Logging started: {filename}")
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
            gains = {
                'kp_left': self.kp_left,
                'ki_left': self.ki_left,
                'kd_left': self.kd_left,
                'kp_right': self.kp_right,
                'ki_right': self.ki_right,
                'kd_right': self.kd_right,
                'timestamp': datetime.now().isoformat()
            }
            with open(filename, 'w') as f:
                json.dump(gains, f, indent=2)
            print(f"Gains saved to {filename}")
        except IOError as e:
            print(f"Error saving gains: {e}")
    
    def load_gains_from_file(self, filename):
        """Load PID gains from JSON file."""
        try:
            with open(filename, 'r') as f:
                gains = json.load(f)
            self.kp_left = gains.get('kp_left', self.kp_left)
            self.ki_left = gains.get('ki_left', self.ki_left)
            self.kd_left = gains.get('kd_left', self.kd_left)
            self.kp_right = gains.get('kp_right', self.kp_right)
            self.ki_right = gains.get('ki_right', self.ki_right)
            self.kd_right = gains.get('kd_right', self.kd_right)
            print(f"Gains loaded from {filename}")
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
        distance_left = self.session_total_ticks_left * ROBOT_CONFIG.METERS_PER_TICK_LEFT
        distance_right = self.session_total_ticks_right * ROBOT_CONFIG.METERS_PER_TICK_RIGHT
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


def _print_live_display(state: PIDTunerState):
    """Print the live display line."""
    # Using \r and end='' for single line updates
    status = (f"[PID] kP_l={state.kp_left:.2f} kI_l={state.ki_left:.2f} kD_l={state.kd_left:.2f} " +
              f"kP_r={state.kp_right:.2f} kI_r={state.ki_right:.2f} kD_r={state.kd_right:.2f} | " +
              f"tgt_L={state.target_vel_left:.2f} tgt_R={state.target_vel_right:.2f} | " +
              f"L: act={state.actual_vel_left:.3f} err={state.error_left:+.3f} | " +
              f"R: act={state.actual_vel_right:.3f} err={state.error_right:+.3f}")
    # Pad to terminal width and use carriage return
    print(status.ljust(140)[:140], end='\r', flush=True)


def interactive_pid_test(port=None):
    """
    Interactive PID tuning CLI for differential drive robot velocity control.
    
    Commands:
    - pid <kp> <ki> <kd>              — set same gains for both wheels
    - pid <kpl> <kil> <kdl> <kpr> <kir> <kdr> — set independent gains
    - vel <speed> [duration]          — command velocity (m/s) for duration (s, default 10s)
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
    state = PIDTunerState()
    active_command = None  # Track current velocity command for repeated sending
    command_end_time = None
    command_start_time = None
    command_duration = 0
    display_last_time = time.time()
    run_active = False
    
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
    print("Interactive PID Tuning CLI - Differential Drive Robot Velocity Control")
    print("="*100)
    print("Commands: pid, vel, step, stop, log, save, load, gains, quit")
    print("Type 'help' for detailed command information.")
    print("="*100 + "\n")
    
    try:
        while True:
            # If active command is running, show live display and re-send
            if active_command is not None:
                now = time.time()
                
                # Check if command should timeout
                if command_end_time is not None and now >= command_end_time:
                    # Stop the command
                    serial_manager.send(Command.stop())
                    active_command = None
                    
                    # Calculate actual elapsed time
                    actual_duration = now - command_start_time if command_start_time else command_duration
                    
                    with lock:
                        state.target_vel_left = 0.0
                        state.target_vel_right = 0.0
                        run_active = False
                        # Report session statistics
                        state.report_session_stats(actual_duration)
                    
                    command_end_time = None
                    command_start_time = None
                    print()
                    continue
                
                # Show live display
                if now - display_last_time >= DISPLAY_INTERVAL:
                    with lock:
                        _print_live_display(state)
                        if state.logging_enabled:
                            state.log_data()
                    display_last_time = now
                
                # Resend command to avoid motor watchdog timeout
                serial_manager.send(active_command)
                time.sleep(SEND_INTERVAL)
                continue
            
            # No active command - prompt for input (blocking)
            try:
                raw = input("pid> ").strip()
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
                print("  pid <kp> <ki> <kd>              - Set same gains for both wheels")
                print("  pid <kpl> <kil> <kdl> <kpr> <kir> <kdr> - Set independent gains")
                print("  vel <speed> [duration]          - Command velocity (m/s) for duration (s, default 10s)")
                print("  step <speed> [duration]         - Step response test (default 3s)")
                print("  stop                            - Stop motors immediately")
                print("  log <filename>                  - Toggle CSV logging")
                print("  save <filename>                 - Save gains to JSON")
                print("  load <filename>                 - Load gains from JSON")
                print("  gains                           - Print current gains")
                print("  quit                            - Exit\n")
            
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
                        
                        # Send PID command
                        pid_cmd = Command(
                            ID="",
                            command_type=CommandType.PID,
                            command=PIDCommand(
                                p_left=state.kp_left,
                                i_left=state.ki_left,
                                d_left=state.kd_left,
                                p_right=state.kp_right,
                                i_right=state.ki_right,
                                d_right=state.kd_right
                            ),
                            pause_duration=0,
                            duration=0
                        )
                        serial_manager.send(pid_cmd)
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
                        
                        # Send PID command
                        pid_cmd = Command(
                            ID="",
                            command_type=CommandType.PID,
                            command=PIDCommand(
                                p_left=state.kp_left,
                                i_left=state.ki_left,
                                d_left=state.kd_left,
                                p_right=state.kp_right,
                                i_right=state.ki_right,
                                d_right=state.kd_right
                            ),
                            pause_duration=0,
                            duration=0
                        )
                        serial_manager.send(pid_cmd)
                        print(f"✓ PID gains set independently:")
                        print(f"  Left:  kP={kpl:.2f} kI={kil:.2f} kD={kdl:.2f}")
                        print(f"  Right: kP={kpr:.2f} kI={kir:.2f} kD={kdr:.2f}\n")
                    except ValueError:
                        print("✗ Invalid number format. Example: pid 1.5 0.0 0.2 1.8 0.0 0.25\n")
                else:
                    print("✗ PID requires either 3 or 6 arguments\n")
            
            elif cmd_name == "vel":
                if len(args) < 1 or len(args) > 2:
                    print("✗ vel requires 1-2 arguments: speed [duration]\n")
                    continue
                
                try:
                    speed = float(args[0])
                    duration = float(args[1]) if len(args) > 1 else 10.0  # Default 10 seconds
                    
                    if not (-ROBOT_CONFIG.MAX_LINEAR_VEL <= speed <= ROBOT_CONFIG.MAX_LINEAR_VEL):
                        print(f"✗ Speed must be between -{ROBOT_CONFIG.MAX_LINEAR_VEL:.2f} and {ROBOT_CONFIG.MAX_LINEAR_VEL:.2f} m/s\n")
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
                    print(f"✓ Velocity command: {speed:.2f} m/s for {duration:.1f}s")
                    print("Live display:\n")
                except ValueError:
                    print("✗ Invalid speed or duration value\n")
            
            elif cmd_name == "step":
                if len(args) < 1 or len(args) > 2:
                    print("✗ step requires 1-2 arguments: speed [duration]\n")
                    continue
                
                try:
                    speed = float(args[0])
                    duration = float(args[1]) if len(args) > 1 else 3.0  # Default 3 seconds
                    
                    if not (0 < speed <= ROBOT_CONFIG.MAX_LINEAR_VEL):
                        print(f"✗ Speed must be between 0 and {ROBOT_CONFIG.MAX_LINEAR_VEL:.2f} m/s\n")
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
