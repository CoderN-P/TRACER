import logging
import time
import threading
from . import ROBOT_CONFIG
from .models import SerialManager, Robot, Command, CommandType, MotorCommand


def calibrate_kv(resolution, duration_sec, port=None):
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


    serial_manager = SerialManager(port, 115200)
    serial_manager.start_read(callback=callback)

    cur_time = time.time()

    speed_left = 0.3 * ROBOT_CONFIG.MAX_LINEAR_VEL
    speed_right = 0.3 * ROBOT_CONFIG.MAX_LINEAR_VEL

    kV_left = []
    kV_right = []

    while True:  
        
        serial_manager.send(
            Command(
                ID="",
                command_type=CommandType.MOTOR,
                command=MotorCommand(
                    left_motor=speed_left,
                    right_motor=speed_right,
                ),
                duration=0,
                pause_duration=0,
            )

        )
        time.sleep(duration_sec)
        serial_manager.send(Command.stop())

        with lock:
            left_actual_speed = left_encoder / duration_sec * ROBOT_CONFIG.METERS_PER_TICK_LEFT
            right_actual_speed = right_encoder / duration_sec * ROBOT_CONFIG.METERS_PER_TICK_RIGHT
             
            pwm_left = speed_left / ROBOT_CONFIG.MAX_LINEAR_VEL
            pwm_right = speed_right / ROBOT_CONFIG.MAX_LINEAR_VEL
            
            left_kV = (pwm_left - 0.2) / left_actual_speed if left_actual_speed > 0 else float('inf')
            right_kV = (pwm_right - 0.1) / right_actual_speed if right_actual_speed > 0 else float('inf')
            
            logger.info(f"Left wheel encoder ticks {left_encoder:.4f} ticks")
            logger.info(f"Right wheel encoder ticks: {right_encoder:.4f} ticks")
            logger.info(f"LEFT PWM value tested: {pwm_left:.2f}")
            logger.info(f"RIGHT PWM value tested: {pwm_right:.2f}")
            logger.info(f"Left wheel speed: {left_actual_speed:.2f} m/s")
            logger.info(f"Right wheel speed: {right_actual_speed:.2f} m/s")
            logger.info(f"Left wheel kV: {left_kV:.2f}")
            logger.info(f"Right wheel kV: {right_kV:.2f}")
            
            kV_left.append(left_kV)
            kV_right.append(right_kV)

            left_encoder = 0
            right_encoder = 0

        speed_left += resolution*ROBOT_CONFIG.MAX_LINEAR_VEL # resolution in pwm percentage
        speed_right += resolution*ROBOT_CONFIG.MAX_LINEAR_VEL

        if speed_left > ROBOT_CONFIG.MAX_LINEAR_VEL or speed_right > ROBOT_CONFIG.MAX_LINEAR_VEL:
            logger.info("Evaluated kV values:")
            estimated_kV_left = sum(kV_left) / len(kV_left) if kV_left else float('inf')
            estimated_kV_right = sum(kV_right) / len(kV_right) if kV_left else float('inf')
            logger.info(f"Estimated kS for left wheel: {estimated_kV_left:.2f}")
            logger.info(f"Estimated kS for right wheel: {estimated_kV_right:.2f}")
            return
        
        
        
        
        
        