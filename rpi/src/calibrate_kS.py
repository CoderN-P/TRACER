import logging
import time
import threading
from . import ROBOT_CONFIG
from .models import SerialManager, Robot, Command, CommandType, MotorPWMCommand, StateEstimator


def calibrate_ks(resolution, duration_sec, port=None):
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
        if not data: return
        
        sensor_data = Robot.bytes_to_sensor_data(data)
        nonlocal left_encoder, right_encoder
        with lock:
            left_encoder += sensor_data.left_encoder
            right_encoder += sensor_data.right_encoder
            

    serial_manager = SerialManager(port, 921600)
    serial_manager.start_read(callback=callback)

    cur_time = time.time()
    
    pwm_left = 0.3
    pwm_right = 0.3
    
    ks_left = 0
    ks_right = 0
    
    while time.time() - cur_time < 60:  # Run for up to 60 seconds, or until we find the kS values
        serial_manager.send(
            Command(
                ID="",
                command_type=CommandType.PWM,
                command=MotorPWMCommand(
                    left_motor=pwm_left,
                    right_motor=pwm_right,
                ),
                duration=0,
                pause_duration=0,
            )
            
        )
        time.sleep(duration_sec)
        serial_manager.send(Command.stop())
        
        with lock:
            logger.info(f"Left wheel encoder ticks {left_encoder:.4f} ticks")
            logger.info(f"Right wheel encoder ticks: {right_encoder:.4f} ticks")
            logger.info(f"LEFT PWM value tested: {pwm_left:.2f}")
            logger.info(f"RIGHT PWM value tested: {pwm_right:.2f}")
            logger.info("If the robot moved at all, even a little bit, then the kS value is likely below this speed. If it didn't move, then the kS value is likely above this speed.")
            
            if left_encoder == 0:
                ks_left = pwm_left + resolution
            
            if right_encoder == 0:
                ks_right = pwm_right + resolution
                
            if left_encoder == 0 and right_encoder == 0:
                logger.info("Evaluated kS values:")
                logger.info(f"Estimated kS for left wheel: {ks_left:.2f}")
                logger.info(f"Estimated kS for right wheel: {ks_right:.2f}")
                return
                
            left_encoder = 0
            right_encoder = 0
        
        pwm_left -= resolution
        pwm_right -= resolution
        
        if pwm_left < resolution and pwm_right < resolution:
            logger.info("Evaluated kS values:")
            logger.info(f"Estimated kS for left wheel: {ks_left:.2f}")
            logger.info(f"Estimated kS for right wheel: {ks_right:.2f}")
            return
        
        
        
        
        
        