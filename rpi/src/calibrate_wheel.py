# Runs motors at a given speed for a given amount of time, then prints the distance traveled by the wheel. This is used to calibrate the wheel's distance per rotation.
import logging
import time
import threading
from . import ROBOT_CONFIG
from .models import SerialManager, Robot, Command, CommandType, MotorPWMCommand


def calibrate_wheel(pwm, duration_sec, port=None):
    port = port if port else SerialManager.find_port()

    logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

    logger = logging.getLogger(__name__)
    
    if not port:
        logger.error("No serial port found. Please connect the robot.")
        return

    left_encoder = 0
    right_encoder = 0
    packet_count = 0
    prev_sensor_data = None

    lock = threading.Lock()

    def callback(data):
        if not data: return


        sensor_data = Robot.bytes_to_sensor_data(data)

        nonlocal left_encoder, right_encoder, prev_sensor_data, packet_count
        
        packet_count += 1
        
        with lock:
            if prev_sensor_data is not None:
                left_encoder += (sensor_data.left_encoder - prev_sensor_data.left_encoder)
                right_encoder += (sensor_data.right_encoder - prev_sensor_data.right_encoder)
            prev_sensor_data = sensor_data
    
        
    serial_manager = SerialManager(port, 921600)
    
    logger.info(f"Running motors at PWM: {pwm*100}% for {duration_sec} seconds...")
    
    cur_time = time.time()
    
    serial_manager.send(
        Command(
            ID="",
            command_type=CommandType.PWM,
            command=MotorPWMCommand(
                left_motor=pwm,
                right_motor=pwm,
             ),
            duration=0,
            pause_duration=0,
        )
    )

    serial_manager.start_read(callback=callback)

    end_time = cur_time + duration_sec

    while time.time() < end_time:
        time.sleep(0.01)
        
    # slow down gradually to avoid jerking the robot and throwing off the final readings
    serial_manager.send(Command.stop())

    serial_manager.stop()
    
    with lock:
        left_distance = left_encoder * ROBOT_CONFIG.METERS_PER_TICK_LEFT
        right_distance = right_encoder * ROBOT_CONFIG.METERS_PER_TICK_RIGHT
        logger.info(f"Total packets received: {packet_count}")
        logger.info(f"Left wheel distance traveled: {left_distance:.4f} meters")
        logger.info(f"Right wheel distance traveled: {right_distance:.4f} meters")
        logger.info(f"Average distance traveled: {(left_distance + right_distance) / 2:.4f} meters")
        logger.info(f"Measure the true distance traveled by the wheel (e.g. by marking the wheel and counting rotations), then calculate the correction factor as: correction_factor = true_distance / [direction]_distance for each motor to get corrected versions of METERS_PER_TICK_LEFT and METERS_PER_TICK_RIGHT.")
    
    
    
    
    
        
        
        
        
        
    
    
