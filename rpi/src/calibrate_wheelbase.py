import logging
import time
import threading
from . import ROBOT_CONFIG
from .models import SerialManager, Robot, Command, CommandType, MotorCommand


def calibrate_wheelbase(speed, duration_sec, port=None):
    port = port if port else SerialManager.find_port()

    logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

    logger = logging.getLogger(__name__)

    if not port:
        logger.error("No serial port found. Please connect the robot.")
        return

    left_distance = 0
    right_distance = 0
    prev_sensor_data = None

    lock = threading.Lock()

    def callback(data):
        if not data: return


        sensor_data = Robot.bytes_to_sensor_data(data)

        nonlocal left_distance, right_distance, prev_sensor_data
        with lock:
            if prev_sensor_data is not None:
                left_distance += (sensor_data.left_encoder - prev_sensor_data.left_encoder) * ROBOT_CONFIG.METERS_PER_TICK_LEFT
                right_distance += (sensor_data.right_encoder - prev_sensor_data.right_encoder) * ROBOT_CONFIG.METERS_PER_TICK_RIGHT

            prev_sensor_data = sensor_data

    serial_manager = SerialManager(port, 921600)
    serial_manager.start_read(callback=callback)

    logger.info(f"Spinning motors at {speed} m/s for {duration_sec} seconds...")

    cur_time = time.time()

    # Create motor command for differential spin (turning in place)
    motor_command = Command(
        ID="",
        command_type=CommandType.MOTOR,
        command=MotorCommand(
            left_motor=-speed,
            right_motor=speed,
        ),
        duration=0,
        pause_duration=0,
    )

    # Send motor commands every 20ms to keep the robot alive
    while time.time() - cur_time < duration_sec:
        serial_manager.send(motor_command)
        time.sleep(0.02)

    serial_manager.send(Command.stop())

    with lock:
        logger.info(f"Left wheel distance traveled: {left_distance:.4f} meters")
        logger.info(f"Right wheel distance traveled: {right_distance:.4f} meters")
        logger.info(f"Estimated heading change: {(left_distance - right_distance) / ROBOT_CONFIG.WHEEL_BASE:.4f} radians")
        logger.info(f"Estimated heading change: {(left_distance - right_distance) / ROBOT_CONFIG.WHEEL_BASE * (180 / 3.14159):.2f} degrees")
        logger.info(f"Measure the actual heading change using a protractor or by tracking the robot's path, and use the ratio of actual to estimated heading change to calculate the correction factor for the wheelbase.")