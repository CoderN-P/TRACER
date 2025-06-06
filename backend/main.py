import time
from flask import Flask
from flask_socketio import SocketIO
import socketio
from Controller import Controller
import threading


app = Flask(__name__)
socket = SocketIO(app, cors_allowed_origins='*')
sio_client = socketio.Client()


def setup_routes(controller: Controller):
    @socket.on('query')
    def handle_query(data):
        """
        Handle a text query command to the robot.
        """
        sio_client.emit('query', data)
        
    @socket.on('joystick_input')
    def handle_ui_joystick_input(data):
        """
        Handle joystick input from the UI.
        """
        print(data)
        #controller.handle_joystick_input(data)
        
    @sio_client.on('rumble')
    def handle_rumble(data):
        print(f"Rumble command received: {data}")
        #controller.rumble(data['low'], data['high'], data['duration'])
        
    @sio_client.on('sensor_data')
    def handle_sensor_update(data):
        socket.emit('sensor_data', data)
        
    @sio_client.event
    def connect():
        print("Connected to RPi backend")
    

def start_socket_server():
    """
    Start the Flask-SocketIO server.
    """
    socket.run(app, host='0.0.0.0', port=8080)

if __name__ == "__main__":
    # Init joystick
    controller = Controller.initialize(sio_client, socket)
    setup_routes(controller)

    # Connect to RPi backend
    sio_client.connect('http://192.168.4.119:8080')

    # Start socket server in a background thread
    threading.Thread(target=start_socket_server, daemon=True).start()

    # Main loop for joystick input (main thread = avoids macOS issues)
    try:
        while True:
            controller.send_update()
            time.sleep(0.05)  # 20 Hz
    except KeyboardInterrupt:
        print("Shutting down.")