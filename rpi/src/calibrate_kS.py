import logging
import time
import threading
from . import ROBOT_CONFIG
from .models import SerialManager, Robot, Command, CommandType, MotorCommand


def calibrate_ks(resolution, duration_sec):
    port = SerialManager.find_port()
    if not port:
        logging.error("No serial port found. Please connect the robot.")
        return

    left_encoder = 0
    right_encoder = 0

    lock = threading.Lock()

    def callback(data):
        if not data: return


        sensor_data = Robot.bytes_to_sensor_data(data)

        nonlocal left_encoder, right_encoder
        with lock:
            left_encoder = sensor_data.left_encoder
            right_encoder = sensor_data.right_encoder
            

    serial_manager = SerialManager(port, 115200)
    serial_manager.start_read(callback=callback)

    cur_time = time.time()
    
    speed_left = ROBOT_CONFIG.MAX_LINEAR_VEL_LEFT / 2
    speed_right = ROBOT_CONFIG.MAX_LINEAR_VEL_RIGHT / 2
    
    # kV = speed * MAX_PWM / max_speed
    # kS = min PWM (0-1) needed to overcome static friction and start moving the robot. We can estimate this by running the motors at a low speed and seeing which level actually gets movement.
    # So, with simple linear feedforward and no kS yet, PWM = cur_speed / max_speed.
    ks_left = 0
    ks_right = 0
    
    while time.time() - cur_time < duration_sec:
        serial_manager.send(
            Command(
                command_type=CommandType.MOTOR,
                command=MotorCommand(
                    left_motor=speed_left,
                    right_motor=speed_right,
                ),
            )
        )
        time.sleep(duration_sec)
        serial_manager.send(Command.stop())
        
        with lock:
            logging.info(f"Left wheel encoder ticks {left_encoder:.4f} meters")
            logging.info(f"Right wheel encoder ticks: {right_encoder:.4f} meters")
            logging.info(f"LEFT PWM value tested: {speed_left / ROBOT_CONFIG.MAX_LINEAR_VEL_LEFT:.2f}")
            logging.info(f"RIGHT PWM value tested: {speed_right / ROBOT_CONFIG.MAX_LINEAR_VEL_RIGHT:.2f}")
            logging.info("If the robot moved at all, even a little bit, then the kS value is likely below this speed. If it didn't move, then the kS value is likely above this speed.")
            
            if left_encoder == 0:
                ks_left = (speed_left + 0.05) / ROBOT_CONFIG.MAX_LINEAR_VEL_LEFT
            
            if right_encoder == 0:
                ks_right = (speed_right + 0.05) / ROBOT_CONFIG.MAX_LINEAR_VEL_RIGHT
                
            if left_encoder == 0 and right_encoder == 0:
                logging.info("Evaluated kS values:")
                logging.info(f"Estimated kS for left wheel: {ks_left:.2f}")
                logging.info(f"Estimated kS for right wheel: {ks_right:.2f}")
                return
                
            left_encoder = 0
            right_encoder = 0
        
        speed_left -= resolution
        speed_right -= resolution
        
        if speed_left < resolution and speed_right < resolution:
            logging.info("Evaluated kS values:")
            logging.info(f"Estimated kS for left wheel: {ks_left:.2f}")
            logging.info(f"Estimated kS for right wheel: {ks_right:.2f}")
            return
        
        
        
        
        
        