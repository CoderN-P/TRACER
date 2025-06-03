import asyncio
from src import Robot, SerialManager, run_socket_server, socketio

async def main():
    serial_manager = SerialManager('/dev/ttyUSB0', 115200)
    robot = Robot(serial_manager, socketio)
    await serial_manager.start(robot)

    # If run_socket_server is blocking, run it in a thread or separately
    run_socket_server(robot)

if __name__ == "__main__":
    asyncio.run(main())