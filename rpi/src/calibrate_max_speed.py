import logging
import time
import threading
from . import ROBOT_CONFIG
from .models import SerialManager, Robot, Command, CommandType, MotorPWMCommand


def calibrate_max_speed(port=None):
    port = port if port else SerialManager.find_port()

    logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

    logger = logging.getLogger(__name__)

    if not port:
        logger.error("No serial port found. Please connect the robot.")
        return

    left_encoder = 0
    right_encoder = 0
    prev_sensor_data = None

    lock = threading.Lock()

    def callback(data):
        if not data: return


        sensor_data = Robot.bytes_to_sensor_data(data)

        nonlocal left_encoder, right_encoder, prev_sensor_data
        with lock:
            if prev_sensor_data is not None:
                left_encoder += (sensor_data.left_encoder - prev_sensor_data.left_encoder)
                right_encoder += (sensor_data.right_encoder - prev_sensor_data.right_encoder)
            prev_sensor_data = sensor_data


    serial_manager = SerialManager(port, 921600)
    serial_manager.start_read(callback=callback)

    cur_time = time.time()

    
    serial_manager.send(
        Command(
            ID="",
            command_type=CommandType.PWM,
            command=MotorPWMCommand(
                left_motor=1.0,
                right_motor=1.0,
            ),
            duration=0,
            pause_duration=0,
        )
    )
    
    
    # Wait to reach steady state
    while time.time() - cur_time < 1:
        time.sleep(0.02)
        
    left_encoder = 0
    right_encoder = 0
    
    cur_time = time.time()

    # Run at full speed for 1 second to measure max speed
    while time.time() - cur_time < 1:
        time.sleep(0.02)
        
    serial_manager.send(Command.stop())
    
    with lock:
        logger.info(f"Total encoder ticks: Left = {left_encoder}, Right = {right_encoder}")
        logger.info(f"Total time elapsed: {time.time() - cur_time:.2f} seconds")
        left_speed = (left_encoder * ROBOT_CONFIG.METERS_PER_TICK_LEFT) / (time.time() - cur_time)
        right_speed = (right_encoder * ROBOT_CONFIG.METERS_PER_TICK_RIGHT) / (time.time() - cur_time)
        
        logger.info(f"Max speed: Left = {left_speed:.2f} m/s, Right = {right_speed:.2f} m/s")
        logger.info(f"Global MAX_LINEAR_VEL: {min(left_speed, right_speed):.2f} m/s")
        
        
        
        
        
        