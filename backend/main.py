import time

import requests
from flask import Flask
from flask_socketio import SocketIO
import socketio
from Controller import Controller
import threading

from GestureController import GestureController

app = Flask(__name__)
socket = SocketIO(app, cors_allowed_origins='*')
sio_client = socketio.Client()  # Use WebSocket transport for better performance
gesture_controller_route = "http://192.168.4.47/sensors" # esp32 running gesture controller code, serving sensor data at this endpoint
AP = "http://10.42.0.1:8080"
NORMAL = "http://192.168.4.119:8080"

def setup_routes(controller: Controller):
    @socket.on('query')
    def handle_query(data):
        """
        Handle a text query command to the robot.
        """
        sio_client.emit('query', data)
        
    @socket.on('set_state')
    def handle_state(data):
        """
        Handle a state change command from the UI.
        Expected payload for PATH_FOLLOWING:
          {
            state: "PATH_FOLLOWING",
            path_type: "freehand" | "spline",
            path: [{x, y}, ...]           # freehand: array of {x, y} points in meters
                | {splines: [...]}        # spline: exportToJSON() structure
          }
        """
        controller.rumble(0.5, 0.5, 500) # Rumble for feedback
        
        if data.get("state") == "PATH_FOLLOWING" and not data.get("path"):
            return
        
        sio_client.emit('set_state', data)
        
    @socket.on('joystick_input')
    def handle_ui_joystick_input(data):
        """
        Handle joystick input from the UI.
        """
        controller.handle_joystick_input(data)
        
    @sio_client.on('obstacle_detected')
    def handle_obstacle_detected(data):
        controller.on_obstacle_detected(data)
        socket.emit('obstacle_detected', data)
        
    @sio_client.on('cliff_detected')
    def handle_cliff_detected(data):
        controller.on_cliff_detected(data)
        socket.emit('cliff_detected', data)
        
    @sio_client.on('sensor_data')
    def handle_sensor_update(data):
        socket.emit('sensor_data', data)
        
    @sio_client.on('active_command')
    def handle_active_command(data):
        socket.emit('active_command', data)
        
    @sio_client.on('path_complete')
    def handle_path_complete(data):
        """
        Forwarded from the RPi when the robot finishes executing a path.
        """
        controller.rumble(0.5, 0.5, 500)
        socket.emit('path_complete', data)
        
    @socket.on('play_recording')
    def handle_play_recording(data):
        """
        Handle the play recording command.
        """
        controller.play_recording(data["timestamp"])
        
    @socket.on('stop_recording')
    def handle_stop_recording():
        """
        Handle the stop recording command.
        """
        controller.stop_recording()
    
    @socket.on('start_recording')
    def handle_start_recording():
        """
        Handle the start recording command.
        """
        controller.start_recording()
        
    @socket.on('precision_mode')
    def handle_toggle_precision_mode(data):
        """
        Toggle precision mode for the robot.
        """
        controller.toggle_precision_mode()
    
    @socket.on('joystick_mode')
    def handle_joystick_mode(data):
        """
        Handle joystick mode toggle.
        """
        controller.manage_state(data['mode'])
        
    @socket.on('stop')
    def stop():
        controller.rumble(0.5, 0.5, 1)
        sio_client.emit("stop")
        
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

    # Start the gesture controller sensor loop

    gesture_controller = GestureController(gesture_controller_route, socket)
    gesture_controller.start_sensor_loop()
    
    controller = Controller.initialize(sio_client, socket, gesture_controller)
    # controller = Controller.initialize(sio_client, socket)
    setup_routes(controller)
    # # Connect to RPi backend
    sio_client.connect(NORMAL, transports=['polling'])


    # Start socket server in a background thread
    threading.Thread(target=start_socket_server, daemon=True).start()
    

    # Main loop for joystick input (main thread = avoids macOS issues)
    
    try:
        while True:
            controller.send_update()
            time.sleep(0.05)  # 20 Hz
    except KeyboardInterrupt:
        print("Shutting down.")
    