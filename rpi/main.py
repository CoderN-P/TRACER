import asyncio
from src import Robot, SerialManager, run_socket_server, socketio

async def main():
    serial_manager = SerialManager('/dev/ttyUSB0', 115200)
    robot = Robot(serial_manager, socketio)

    await asyncio.gather(
        serial_manager.start(robot),   # or .run_loop(robot)
        run_socket_server(robot),
        robot.start()  # Start the robot's background tasks
    )

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())  # avoids nested loop error