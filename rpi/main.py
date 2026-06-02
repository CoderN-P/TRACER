import sys
import argparse
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()
from src import text_to_command
import os

from src import Robot, SerialManager, run_socket_server, socketio, ROBOT_CONFIG, serial_test, calibrate_feedforward, calibrate_max_speed, interactive_test, calibrate_mag, visualize_feedforward

parser = argparse.ArgumentParser(
    prog="TRACER RPI",
    description="Main control program for TRACER robot running on Raspberry Pi. Handles serial communication with the robot's microcontroller and serves a Socket.IO API for remote control and telemetry.",
)

parser.add_argument('--speed', type=float, default=ROBOT_CONFIG.MAX_LINEAR_VEL, help="Speed in m/s to run the motors during wheel calibration (default: Robot max vel).")
parser.add_argument('--duration', type=float, default=2.0, help="Duration in seconds to run the motors during wheel calibration (default: 2 seconds).")
parser.add_argument('--resolution', type=float, default=0.1, help="Time resolution in seconds for testing different PWM values during kS calibration (default: 0.1 seconds).")
parser.add_argument('--serial-test', action='store_true', help="Run a test that continuously prints out sensor packets from the robot to verify serial communication and packet parsing.")
parser.add_argument('--port', type=str, default=None, help="Serial port to use for communication with the robot (default: auto-detect).")
parser.add_argument('--calibrate-feedforward', action='store_true', help="Run the feedforward calibration routine to determine the lookup tables for motor velocity feedforward.")
parser.add_argument('--visualize-feedforward', action='store_true', help="Plot all feedforward LUT JSON files and generate an averaged LUT JSON.")
parser.add_argument('--calibrate-max-speed', action='store_true', help="Run the max speed calibration routine to determine the maximum achievable speed of the robot at full motor power.")
parser.add_argument('--calibrate-mag', action='store_true', help="Calibrate the magnetometer using hard and soft iron calibration.")
parser.add_argument('--interactive-test', action='store_true', help="Run interactive velocity / PID / PWM test CLI")
parser.add_argument("--timeout", type=float, default=1.0, help="No-data timeout before mag calibration (seconds)")
parser.add_argument('--output-json', type=str, default=None, help="Optional output dir for averaged LUT JSON or output filename for normal LUT JSON.")
parser.add_argument('--show-plots', action='store_true', help="Display plot windows in addition to saving PNG files.")

async def main(p):
    port = p if p else SerialManager.find_port()
    if not port:
        logging.error("No serial port found. Please connect the robot.")
        
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(threadName)s | %(name)s | %(levelname)s | %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)] # Explicitly add StreamHandler
    )
    serial_manager = SerialManager(port, 921600)
    robot = Robot(serial_manager, socketio)
    logging.getLogger('socketio').setLevel(logging.ERROR)
    logging.getLogger('engineio').setLevel(logging.ERROR)
    robot._logger.setLevel(logging.INFO)        
    serial_manager.start(robot, robot.loop)  # Start background serial read thread; dispatch sensor packets on robot loop
    robot.start()

    try:
        await run_socket_server(robot)
    finally:
        serial_manager.stop()
        robot.stop()

if __name__ == "__main__":
    hostname = os.uname().nodename
    print(f"Running on hostname: {hostname}")
    
    args = parser.parse_args()
        
    if args.serial_test:
        serial_test(args.port)
    elif args.calibrate_feedforward:
        calibrate_feedforward(args.resolution, args.duration, args.output_json, args.port)
    elif args.visualize_feedforward:
        visualize_feedforward(
            output_json_path=args.output_json,
            show_plots=args.show_plots,
        )
    elif args.calibrate_max_speed:
        calibrate_max_speed(args.port)
    elif args.interactive_test:
        interactive_test(args.port)
    elif args.calibrate_mag:
        calibrate_mag(args.port, args.timeout)
    else:
        asyncio.run(main(args.port))