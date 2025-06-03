from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*')

def setup_routes(robot):
    @socketio.on('joystick_input')
    def on_joystick(data):
        robot.handle_joystick_input(data)
        
    @socketio.on('query')
    def on_query(data):
        robot.handle_query(data["query"])
        
    @socketio.on('connect')
    def on_connect():
        print("Client connected")
        

def run_socket_server(robot):
    setup_routes(robot)
    socketio.run(app, host='0.0.0.0', port=8080)
