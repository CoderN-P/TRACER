import asyncio
import logging
from src import text_to_command
import os
from dotenv import load_dotenv
load_dotenv()
from src import Robot, SerialManager, run_socket_server, socketio

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
    logging.info(f"Running on hostname: {hostname}")
    if hostname == "tracer":
        asyncio.run(main())
        
