"""
Velocity Feedforward Calibration using Lookup Tables.

Creates lookup tables of (speed, PWM) pairs for each motor direction (forward/backward).
Uses linear interpolation to accurately estimate PWM for any target velocity.
More accurate than linear regression as it captures nonlinear motor behavior.
"""

import logging
import time
import threading
import json
from pathlib import Path
from . import ROBOT_CONFIG
from .models import SerialManager, Robot, Command, CommandType, MotorPWMCommand, StateEstimator


def linear_interpolate(speed, lookup_table):
    """
    Interpolate PWM value for a given speed using lookup table.
    
    Args:
        speed: Target velocity (m/s)
        lookup_table: List of (speed, pwm) tuples sorted by speed
    
    Returns:
        Interpolated PWM value, or None if out of bounds
    """
    if not lookup_table or len(lookup_table) < 2:
        return None
    
    # Handle out of bounds
    if speed < lookup_table[0][0] or speed > lookup_table[-1][0]:
        return None
    
    # Find the two points to interpolate between
    for i in range(len(lookup_table) - 1):
        speed1, pwm1 = lookup_table[i]
        speed2, pwm2 = lookup_table[i + 1]
        
        if speed1 <= speed <= speed2:
            # Linear interpolation
            if speed2 == speed1:
                return pwm1
            
            fraction = (speed - speed1) / (speed2 - speed1)
            pwm = pwm1 + fraction * (pwm2 - pwm1)
            return pwm
    
    return None


def calibrate_feedforward(resolution, duration_sec, port=None):
    """
    Calibrate motor velocity feedforward using lookup table method.
    
    Sweeps through PWM values from 0 to 1.0 and records actual speeds.
    Creates forward and backward lookup tables for each motor.
    Saves results to JSON for use in feedforward control.
    
    Args:
        resolution: PWM step size (e.g., 0.05 for 5% increments)
        duration_sec: How long to measure at each PWM level
        port: Serial port (auto-detected if None)
    """
    port = port if port else SerialManager.find_port()
    
    logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
    logger = logging.getLogger(__name__)
    
    if not port:
        logger.error("No serial port found. Please connect the robot.")
        return
    
    left_encoder = 0
    right_encoder = 0
    lock = threading.Lock()
    
    def callback(data):
        if not data:
            return
        
        sensor_data = Robot.bytes_to_sensor_data(data)
        nonlocal left_encoder, right_encoder
        with lock:
            left_encoder += sensor_data.left_encoder
            right_encoder += sensor_data.right_encoder
    
    serial_manager = SerialManager(port, 921600)
    serial_manager.start_read(callback=callback)
    
    # Storage for lookup table entries
    # Format: [(speed, pwm), ...]
    forward_left = []
    forward_right = []
    backward_left = []
    backward_right = []
    
    settle_sec = 1.0
    
    # FORWARD DIRECTION: sweep from 0 to 1.0
    logger.info("\n" + "="*80)
    logger.info("FORWARD DIRECTION CALIBRATION")
    logger.info("="*80 + "\n")
    
    pwm_left = resolution
    pwm_right = resolution
    
    while pwm_left <= 1.0 and pwm_right <= 1.0:
        motor_command = Command(
            ID="",
            command_type=CommandType.PWM,
            command=MotorPWMCommand(left_motor=pwm_left, right_motor=pwm_right),
            duration=0,
            pause_duration=0,
        )
        
        # Settle phase
        logger.info(f"Settling for {settle_sec:.1f}s at PWM L={pwm_left:.3f}, R={pwm_right:.3f}...")
        settle_start = time.time()
        while time.time() - settle_start < settle_sec:
            serial_manager.send(motor_command)
            time.sleep(0.02)
        
        # Reset encoders
        with lock:
            left_encoder = 0
            right_encoder = 0
        
        # Measurement phase
        measurement_start = time.time()
        while time.time() - measurement_start < duration_sec:
            serial_manager.send(motor_command)
            time.sleep(0.02)
        measurement_elapsed = time.time() - measurement_start
        
        # Stop and collect data
        serial_manager.send(Command.stop())
        
        with lock:
            left_ticks = left_encoder
            right_ticks = right_encoder
            left_encoder = 0
            right_encoder = 0
            
            left_speed = left_ticks / measurement_elapsed * ROBOT_CONFIG.METERS_PER_TICK_LEFT
            right_speed = right_ticks / measurement_elapsed * ROBOT_CONFIG.METERS_PER_TICK_RIGHT
            
            logger.info(f"  PWM L={pwm_left:.3f} → speed={left_speed:.4f} m/s")
            logger.info(f"  PWM R={pwm_right:.3f} → speed={right_speed:.4f} m/s")
            
            # Validity checks
            MIN_VEL = 0.01
            MAX_VEL = 0.5
            
            if MIN_VEL < left_speed < MAX_VEL:
                forward_left.append((left_speed, pwm_left))
                logger.info(f"  ✓ Left: Added ({left_speed:.4f}, {pwm_left:.3f})")
            else:
                logger.info(f"  ✗ Left: Speed {left_speed:.4f} out of bounds")
            
            if MIN_VEL < right_speed < MAX_VEL:
                forward_right.append((right_speed, pwm_right))
                logger.info(f"  ✓ Right: Added ({right_speed:.4f}, {pwm_right:.3f})")
            else:
                logger.info(f"  ✗ Right: Speed {right_speed:.4f} out of bounds")
        
        pwm_left += resolution
        pwm_right += resolution
        logger.info()
    
    # BACKWARD DIRECTION: sweep from -resolution to -1.0
    logger.info("\n" + "="*80)
    logger.info("BACKWARD DIRECTION CALIBRATION")
    logger.info("="*80 + "\n")
    
    pwm_left = -resolution
    pwm_right = -resolution
    
    while abs(pwm_left) <= 1.0 and abs(pwm_right) <= 1.0:
        motor_command = Command(
            ID="",
            command_type=CommandType.PWM,
            command=MotorPWMCommand(left_motor=pwm_left, right_motor=pwm_right),
            duration=0,
            pause_duration=0,
        )
        
        # Settle phase
        logger.info(f"Settling for {settle_sec:.1f}s at PWM L={pwm_left:.3f}, R={pwm_right:.3f}...")
        settle_start = time.time()
        while time.time() - settle_start < settle_sec:
            serial_manager.send(motor_command)
            time.sleep(0.02)
        
        # Reset encoders
        with lock:
            left_encoder = 0
            right_encoder = 0
        
        # Measurement phase
        measurement_start = time.time()
        while time.time() - measurement_start < duration_sec:
            serial_manager.send(motor_command)
            time.sleep(0.02)
        measurement_elapsed = time.time() - measurement_start
        
        # Stop and collect data
        serial_manager.send(Command.stop())
        
        with lock:
            left_ticks = left_encoder
            right_ticks = right_encoder
            left_encoder = 0
            right_encoder = 0
            
            left_speed = left_ticks / measurement_elapsed * ROBOT_CONFIG.METERS_PER_TICK_LEFT
            right_speed = right_ticks / measurement_elapsed * ROBOT_CONFIG.METERS_PER_TICK_RIGHT
            
            logger.info(f"  PWM L={pwm_left:.3f} → speed={left_speed:.4f} m/s")
            logger.info(f"  PWM R={pwm_right:.3f} → speed={right_speed:.4f} m/s")
            
            # Validity checks
            MIN_VEL = -0.5
            MAX_VEL = -0.01
            
            if MIN_VEL < left_speed < MAX_VEL:
                backward_left.append((left_speed, pwm_left))
                logger.info(f"  ✓ Left: Added ({left_speed:.4f}, {pwm_left:.3f})")
            else:
                logger.info(f"  ✗ Left: Speed {left_speed:.4f} out of bounds")
            
            if MIN_VEL < right_speed < MAX_VEL:
                backward_right.append((right_speed, pwm_right))
                logger.info(f"  ✓ Right: Added ({right_speed:.4f}, {pwm_right:.3f})")
            else:
                logger.info(f"  ✗ Right: Speed {right_speed:.4f} out of bounds")
        
        pwm_left -= resolution
        pwm_right -= resolution
        logger.info()
    
    # Sort lookup tables by speed
    forward_left.sort(key=lambda x: x[0])
    forward_right.sort(key=lambda x: x[0])
    backward_left.sort(key=lambda x: x[0])  # Most negative first
    backward_right.sort(key=lambda x: x[0])
    
    # Display results
    logger.info("\n" + "="*80)
    logger.info("CALIBRATION RESULTS")
    logger.info("="*80 + "\n")
    
    logger.info("FORWARD - LEFT MOTOR:")
    for speed, pwm in forward_left:
        logger.info(f"  Speed: {speed:7.4f} m/s → PWM: {pwm:.3f}")
    
    logger.info("\nFORWARD - RIGHT MOTOR:")
    for speed, pwm in forward_right:
        logger.info(f"  Speed: {speed:7.4f} m/s → PWM: {pwm:.3f}")
    
    logger.info("\nBACKWARD - LEFT MOTOR:")
    for speed, pwm in backward_left:
        logger.info(f"  Speed: {speed:7.4f} m/s → PWM: {pwm:.3f}")
    
    logger.info("\nBACKWARD - RIGHT MOTOR:")
    for speed, pwm in backward_right:
        logger.info(f"  Speed: {speed:7.4f} m/s → PWM: {pwm:.3f}")
    
    # Save to JSON
    feedforward_data = {
        "calibration_method": "lookup_table_with_linear_interpolation",
        "forward_left": forward_left,
        "forward_right": forward_right,
        "backward_left": backward_left,
        "backward_right": backward_right,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Ensure calibration_files/feedforward directory exists
    calibration_dir = Path(__file__).parent.parent / "calibration_files" / "feedforward"
    calibration_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = calibration_dir / "feedforward_lookup_table.json"
    try:
        with open(output_file, 'w') as f:
            json.dump(feedforward_data, f, indent=2)
        logger.info(f"\n✓ Lookup table saved to: {output_file}")
    except Exception as e:
        logger.error(f"✗ Failed to save lookup table: {e}")
    
    # Test interpolation
    logger.info("\n" + "="*80)
    logger.info("INTERPOLATION TEST")
    logger.info("="*80 + "\n")
    
    test_speeds = [0.05, 0.1, 0.15, 0.2, 0.25]
    logger.info("Forward direction interpolation tests:")
    for speed in test_speeds:
        pwm_l = linear_interpolate(speed, forward_left)
        pwm_r = linear_interpolate(speed, forward_right)
        if pwm_l is not None:
            logger.info(f"  Speed {speed:.2f} m/s → Left PWM: {pwm_l:.3f}")
        if pwm_r is not None:
            logger.info(f"  Speed {speed:.2f} m/s → Right PWM: {pwm_r:.3f}")
    
    serial_manager.send(Command.stop())
    serial_manager.stop()
    logger.info("\nCalibration complete!")


if __name__ == "__main__":
    # Calibration parameters
    RESOLUTION = 0.05  # 5% PWM increments
    DURATION_SEC = 2.0  # Measure for 2 seconds at each PWM level
    
    calibrate_feedforward(
        resolution=RESOLUTION,
        duration_sec=DURATION_SEC
    )
