import eventlet
eventlet.monkey_patch()
from src import Robot, SerialManager, run_socket_server, socketio

def main():
    serial_manager = SerialManager('/dev/ttyUSB0', 115200)
    robot = Robot(serial_manager, socketio)
    
    # Use eventlet's green threads instead of Python's threading
    eventlet.spawn(serial_manager.run_loop, robot)
    
    # Run socket server (should be your Flask-SocketIO app)
    run_socket_server(robot)

if __name__ == "__main__":
    main()