import logging
import threading
import time
import math

from . import ROBOT_CONFIG
from .models import SerialManager, Robot, Command, CommandType, MotorCommand, PurePursuit


def _print_run_results(left_ticks, right_ticks, duration_sec):
    left_distance = left_ticks * ROBOT_CONFIG.METERS_PER_TICK_LEFT
    right_distance = right_ticks * ROBOT_CONFIG.METERS_PER_TICK_RIGHT
    avg_distance = (left_distance + right_distance) / 2.0

    left_speed = left_distance / duration_sec if duration_sec > 0 else 0.0
    right_speed = right_distance / duration_sec if duration_sec > 0 else 0.0
    avg_speed = (left_speed + right_speed) / 2.0

    tick_displacement = left_ticks - right_ticks
    distance_displacement = left_distance - right_distance
    
    # Heading delta using wheelbase: theta = (right - left) / wheelbase
    # Negative because left-moving more means robot turns left (negative heading)
    heading_delta_rad = -(distance_displacement) / ROBOT_CONFIG.WHEEL_BASE if ROBOT_CONFIG.WHEEL_BASE > 0 else 0.0
    heading_delta_deg = math.degrees(heading_delta_rad)

    print("\n=== Run Results ===")
    print(f"Duration: {duration_sec:.3f}s")
    print(f"Left ticks:  {left_ticks}")
    print(f"Right ticks: {right_ticks}")
    print(f"Encoder displacement (L-R): {tick_displacement} ticks ({distance_displacement:.4f} m)")
    print(f"Left distance:  {left_distance:.4f} m")
    print(f"Right distance: {right_distance:.4f} m")
    print(f"Average distance: {avg_distance:.4f} m")
    print(f"Left speed:  {left_speed:.4f} m/s")
    print(f"Right speed: {right_speed:.4f} m/s")
    print(f"Average speed: {avg_speed:.4f} m/s")
    print(f"Heading delta: {heading_delta_deg:.2f}°")
    print("===================\n")


def interactive_velocity_test_twist(port=None):
    """Test mode using linear velocity (m/s) and angular velocity (rad/s)."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    logger = logging.getLogger(__name__)

    serial_port = port if port else SerialManager.find_port()
    if not serial_port:
        logger.error("No serial port found. Please connect the robot.")
        return

    left_encoder = 0
    right_encoder = 0
    prev_sensor_data = None
    run_active = False

    lock = threading.Lock()

    def callback(data):
        nonlocal left_encoder, right_encoder, prev_sensor_data
        if not data:
            return

        sensor_data = Robot.bytes_to_sensor_data(data)

        with lock:
            if prev_sensor_data is not None and run_active:
                left_encoder += (sensor_data.left_encoder - prev_sensor_data.left_encoder)
                right_encoder += (sensor_data.right_encoder - prev_sensor_data.right_encoder)
            prev_sensor_data = sensor_data

    serial_manager = SerialManager(serial_port, 115200)
    serial_manager.start_read(callback=callback)

    print("\nInteractive twist (linear + angular) test started.")
    print("Enter: <linear_m_s> <angular_rad_s> <duration_sec>")
    print("Example: 0.20 0.5 2.5")
    print("Type 'q' or 'quit' to exit.\n")

    try:
        while True:
            raw = input("twist> ").strip()
            if not raw:
                continue

            if raw.lower() in {"q", "quit", "exit"}:
                break

            parts = raw.split()
            if len(parts) != 3:
                print("Please enter exactly 3 values: linear angular duration")
                continue

            try:
                linear_vel = float(parts[0])
                angular_vel = float(parts[1])
                duration_sec = float(parts[2])
            except ValueError:
                print("Invalid number format. Example: 0.20 0.5 3.0")
                continue

            if duration_sec <= 0:
                print("Duration must be > 0 seconds")
                continue

            left_target, right_target = PurePursuit.twist_to_wheel_speeds(linear_vel, angular_vel)

            max_vel = ROBOT_CONFIG.MAX_LINEAR_VEL
            if abs(left_target) > max_vel or abs(right_target) > max_vel:
                print(f"Resulting wheel speeds exceed ±{max_vel:.3f} m/s")
                print(f"  Left: {left_target:.3f} m/s, Right: {right_target:.3f} m/s")
                continue

            print(f"  → Left: {left_target:.3f} m/s, Right: {right_target:.3f} m/s")

            with lock:
                left_encoder = 0
                right_encoder = 0
                run_active = True

            serial_manager.send(
                Command(
                    ID="",
                    command_type=CommandType.MOTOR,
                    command=MotorCommand(left_motor=left_target, right_motor=right_target),
                    duration=0,
                    pause_duration=0,
                )
            )

            start_time = time.time()
            while time.time() - start_time < duration_sec:
                time.sleep(0.01)

            serial_manager.send(Command.stop())
            elapsed = time.time() - start_time

            with lock:
                run_active = False
                left_ticks = left_encoder
                right_ticks = right_encoder

            _print_run_results(left_ticks=left_ticks, right_ticks=right_ticks, duration_sec=elapsed)

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        serial_manager.send(Command.stop())
        serial_manager.stop()
        print("Serial connection closed. Goodbye.")


def interactive_velocity_test(port=None):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    logger = logging.getLogger(__name__)

    serial_port = port if port else SerialManager.find_port()
    if not serial_port:
        logger.error("No serial port found. Please connect the robot.")
        return

    left_encoder = 0
    right_encoder = 0
    prev_sensor_data = None
    run_active = False

    lock = threading.Lock()

    def callback(data):
        nonlocal left_encoder, right_encoder, prev_sensor_data
        if not data:
            return

        sensor_data = Robot.bytes_to_sensor_data(data)

        with lock:
            if prev_sensor_data is not None and run_active:
                left_encoder += (sensor_data.left_encoder - prev_sensor_data.left_encoder)
                right_encoder += (sensor_data.right_encoder - prev_sensor_data.right_encoder)
            prev_sensor_data = sensor_data

    serial_manager = SerialManager(serial_port, 115200)
    serial_manager.start_read(callback=callback)

    print("\nInteractive velocity test started (wheel mode).")
    print("Enter: <left_m_s> <right_m_s> <duration_sec>")
    print("Example: 0.20 0.20 2.5")
    print("Type 'twist' to switch to twist mode (linear + angular velocity).")
    print("Type 'q' or 'quit' to exit.\n")

    try:
        while True:
            raw = input("vel> ").strip()
            if not raw:
                continue

            if raw.lower() in {"q", "quit", "exit"}:
                break

            if raw.lower() == "twist":
                serial_manager.send(Command.stop())
                serial_manager.stop()
                interactive_velocity_test_twist(port=serial_port)
                return

            parts = raw.split()
            if len(parts) != 3:
                print("Please enter exactly 3 values: left right duration")
                continue

            try:
                left_target = float(parts[0])
                right_target = float(parts[1])
                duration_sec = float(parts[2])
            except ValueError:
                print("Invalid number format. Example: 0.15 0.10 3.0")
                continue

            if duration_sec <= 0:
                print("Duration must be > 0 seconds")
                continue

            max_vel = ROBOT_CONFIG.MAX_LINEAR_VEL
            if abs(left_target) > max_vel or abs(right_target) > max_vel:
                print(f"Velocity must be within ±{max_vel:.3f} m/s")
                continue

            with lock:
                left_encoder = 0
                right_encoder = 0
                run_active = True

            serial_manager.send(
                Command(
                    ID="",
                    command_type=CommandType.MOTOR,
                    command=MotorCommand(left_motor=left_target, right_motor=right_target),
                    duration=0,
                    pause_duration=0,
                )
            )

            start_time = time.time()
            while time.time() - start_time < duration_sec:
                time.sleep(0.01)

            serial_manager.send(Command.stop())
            elapsed = time.time() - start_time

            with lock:
                run_active = False
                left_ticks = left_encoder
                right_ticks = right_encoder

            _print_run_results(left_ticks=left_ticks, right_ticks=right_ticks, duration_sec=elapsed)

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        serial_manager.send(Command.stop())
        serial_manager.stop()
        print("Serial connection closed. Goodbye.")


if __name__ == "__main__":
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "wheel"
    if mode == "twist":
        interactive_velocity_test_twist()
    else:
        interactive_velocity_test()
