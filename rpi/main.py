import argparse
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()
from src import text_to_command
import os

from src import Robot, SerialManager, run_socket_server, socketio, ROBOT_CONFIG, calibrate_wheel, calibrate_wheelbase, serial_test, calibrate_ks, calibrate_kv

parser = argparse.ArgumentParser(
    prog="TRACER RPI",
    description="Main control program for TRACER robot running on Raspberry Pi. Handles serial communication with the robot's microcontroller and serves a Socket.IO API for remote control and telemetry.",
)

parser.add_argument('--calibrate-wheel', action='store_true', help="Run the wheel calibration routine to determine correction factor (d_true / d_encoder) for accurate distance measurements.")
parser.add_argument('--calibrate-wheelbase', action='store_true', help="Run the wheelbase calibration routine to determine correction factor for accurate heading change measurements.")
parser.add_argument('--speed', type=float, default=ROBOT_CONFIG.MAX_LINEAR_VEL, help="Speed in m/s to run the motors during wheel calibration (default: Robot max vel).")
parser.add_argument('--duration', type=float, default=2.0, help="Duration in seconds to run the motors during wheel calibration (default: 2 seconds).")
parser.add_argument('--calibrate-ks', action='store_true', help="Run the kS calibration routine to determine the static friction voltage for the motors.")
parser.add_argument('--resolution', type=float, default=0.1, help="Time resolution in seconds for testing different PWM values during kS calibration (default: 0.1 seconds).")
parser.add_argument('--serial-test', action='store_true', help="Run a test that continuously prints out sensor packets from the robot to verify serial communication and packet parsing.")
parser.add_argument('--port', type=str, default=None, help="Serial port to use for communication with the robot (default: auto-detect).")
parser.add_argument('--calibrate-kv', action='store_true', help="Run the kV calibration routine to determine the velocity constants for the motors.")
async def main():
    port = SerialManager.find_port()
    if not port:
        logging.error("No serial port found. Please connect the robot.")
        return
    serial_manager = SerialManager(port, 115200)
    robot = Robot(serial_manager, socketio)
    
    loop = asyncio.get_running_loop()
    serial_manager.start(robot, loop)  # Start background serial read thread

    await run_socket_server(robot)

if __name__ == "__main__":
    hostname = os.uname().nodename
    print(f"Running on hostname: {hostname}")
    
    args = parser.parse_args()
        
    if args.calibrate_wheel:
        calibrate_wheel(args.speed, args.duration, args.port)
    elif args.calibrate_wheelbase:
        calibrate_wheelbase(args.speed, args.duration, args.port)
    elif args.calibrate_ks:
        calibrate_ks(args.resolution, args.duration, args.port)
    elif args.serial_test:
        serial_test(args.port)
    elif args.calibrate_kv:
        calibrate_kv(args.resolution, args.duration, args.port)
    else:
        if hostname == "tracer":
            asyncio.run(main())
        else:
            print("Not running on TRACER robot. To run the main control program, please run this script on the Raspberry Pi connected to the robot.")
