import asyncio
from src import Robot, SerialManager, run_socket_server, socketio

async def main():
    serial_manager = SerialManager('/dev/ttyUSB0', 115200)
    robot = Robot(serial_manager, socketio)
    
    loop = asyncio.get_running_loop()
    serial_manager.start(robot, loop)  # Start background serial read thread

    await run_socket_server(robot)

if __name__ == "__main__":
    asyncio.run(main())