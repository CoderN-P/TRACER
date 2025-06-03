import eventlet
import eventlet.wsgi  # This ensures eventlet is properly imported
eventlet.monkey_patch()
import asyncio, threading
from src import Robot, SerialManager, run_socket_server, socketio

async def main():
    serial_manager = SerialManager('/dev/ttyUSB0', 115200)
    robot = Robot(serial_manager, socketio)
    await serial_manager.start(robot)

    # If run_socket_server is blocking, run it in a thread or separately
    server_thread = threading.Thread(target=run_socket_server, args=(robot,))
    server_thread.start()

    await serial_manager.start(robot)

if __name__ == "__main__":
    asyncio.run(main())
