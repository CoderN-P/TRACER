import asyncio
from src import Robot, SerialManager, run_socket_server, socketio

async def main():
    serial_manager = SerialManager('/dev/ttyUSB0', 115200)
    robot = Robot(serial_manager, socketio)

    asyncio.create_task(serial_manager.run_loop(robot))
    run_socket_server(robot)

if __name__ == "__main__":
    asyncio.run(main())