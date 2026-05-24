import logging
import time
import threading
from . import ROBOT_CONFIG
from .models import SerialManager, Robot, Command, CommandType, MotorPWMCommand, StateEstimator


def _linear_regression(xs, ys):
    if len(xs) < 2 or len(ys) < 2 or len(xs) != len(ys):
        return None

    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)

    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:
        return None

    numer = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    slope = numer / denom
    intercept = mean_y - slope * mean_x

    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 1.0

    return slope, intercept, r2


def calibrate_kv(resolution, duration_sec, ks_left, ks_right, port=None):
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
                left_encoder += StateEstimator.encoder_delta(sensor_data.left_encoder, prev_sensor_data.left_encoder)
                right_encoder += StateEstimator.encoder_delta(sensor_data.right_encoder, prev_sensor_data.right_encoder)
            prev_sensor_data = sensor_data


    serial_manager = SerialManager(port, 921600)
    serial_manager.start_read(callback=callback)

    pwm_left = 0.5
    pwm_right = 0.5

    settle_sec = 1.0
    left_speeds = []
    right_speeds = []
    left_pwm_above_ks = []
    right_pwm_above_ks = []

    while True:
        # Create motor command for this PWM level
        motor_command = Command(
            ID="",
            command_type=CommandType.PWM,
            command=MotorPWMCommand(
                left_motor=pwm_left,
                right_motor=pwm_right,
            ),
            duration=0,
            pause_duration=0,
        )

        # Settle phase: send commands every 20ms to keep robot alive
        logger.info(f"Settling for {settle_sec:.1f}s at PWM L={pwm_left:.2f}, R={pwm_right:.2f}...")
        settle_start = time.time()
        while time.time() - settle_start < settle_sec:
            serial_manager.send(motor_command)
            time.sleep(0.02)

        # Reset encoder counters before measurement
        with lock:
            left_encoder = 0
            right_encoder = 0

        # Measurement phase: send commands every 20ms and record timing
        measurement_start = time.time()
        while time.time() - measurement_start < duration_sec:
            serial_manager.send(motor_command)
            time.sleep(0.02)
        measurement_elapsed = time.time() - measurement_start

        # Stop motors
        serial_manager.send(Command.stop())

        # Collect results
        with lock:
            left_ticks = left_encoder
            right_ticks = right_encoder
            left_encoder = 0
            right_encoder = 0

            left_actual_speed = left_ticks / measurement_elapsed * ROBOT_CONFIG.METERS_PER_TICK_LEFT
            right_actual_speed = right_ticks / measurement_elapsed * ROBOT_CONFIG.METERS_PER_TICK_RIGHT

            left_kV = (pwm_left - ks_left) / left_actual_speed if left_actual_speed > 0 else float('inf')
            right_kV = (pwm_right - ks_right) / right_actual_speed if right_actual_speed > 0 else float('inf')

            logger.info(f"Measurement window: {measurement_elapsed:.3f}s")
            logger.info(f"Left wheel encoder ticks: {left_ticks:.4f} ticks")
            logger.info(f"Right wheel encoder ticks: {right_ticks:.4f} ticks")
            logger.info(f"LEFT PWM value tested: {pwm_left:.2f}")
            logger.info(f"RIGHT PWM value tested: {pwm_right:.2f}")
            logger.info(f"Left wheel speed: {left_actual_speed:.2f} m/s")
            logger.info(f"Right wheel speed: {right_actual_speed:.2f} m/s")
            logger.info(f"Left wheel kV: {left_kV:.2f}")
            logger.info(f"Right wheel kV: {right_kV:.2f}")

            MIN_VEL = 0.05
            MIN_DELTA_PWM = 0.03
            MAX_VEL = 0.25

        if (
                MIN_VEL < left_actual_speed < MAX_VEL and
                (pwm_left - ks_left) > MIN_DELTA_PWM
        ):
            left_speeds.append(left_actual_speed)
            left_pwm_above_ks.append(pwm_left - ks_left)

        if (
                MIN_VEL < right_actual_speed < MAX_VEL and
                (pwm_right - ks_right) > MIN_DELTA_PWM
        ):
            right_speeds.append(right_actual_speed)
            right_pwm_above_ks.append(pwm_right - ks_right)

        pwm_left += resolution
        pwm_right += resolution

        if pwm_left > 1.0 or pwm_right > 1.0:
            logger.info("Evaluated kV values via linear regression:")

            left_fit = _linear_regression(left_speeds, left_pwm_above_ks)
            right_fit = _linear_regression(right_speeds, right_pwm_above_ks)

            if left_fit is None:
                logger.info("Left wheel regression failed (insufficient or degenerate data).")
            else:
                left_kV_est, left_intercept, left_r2 = left_fit
                logger.info(f"Estimated kV for left wheel: {left_kV_est:.4f}")
                logger.info(f"Left fit intercept (expected near 0): {left_intercept:.4f}")
                logger.info(f"Left fit R^2: {left_r2:.4f}")

            if right_fit is None:
                logger.info("Right wheel regression failed (insufficient or degenerate data).")
            else:
                right_kV_est, right_intercept, right_r2 = right_fit
                logger.info(f"Estimated kV for right wheel: {right_kV_est:.4f}")
                logger.info(f"Right fit intercept (expected near 0): {right_intercept:.4f}")
                logger.info(f"Right fit R^2: {right_r2:.4f}")

            serial_manager.send(Command.stop())
            serial_manager.stop()
            return