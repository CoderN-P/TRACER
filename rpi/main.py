import asyncio

from src import text_to_command
from src import Robot, SerialManager, run_socket_server, socketio

async def main():
    port = SerialManager.find_port()
    if not port:
        print("No serial port found. Please connect the robot.")
        return
    serial_manager = SerialManager(port, 115200)
    robot = Robot(serial_manager, socketio)
    
    loop = asyncio.get_running_loop()
    serial_manager.start(robot, loop)  # Start background serial read thread

    await run_socket_server(robot)

if __name__ == "__main__":
    asyncio.run(main())
