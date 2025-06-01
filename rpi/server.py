from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)

def setup_routes(robot):
    @socketio.on('joystick_input')
    def on_joystick(data):
        robot.handle_joystick(data)
        
    @socketio.on('query')
    def on_query(data):
        robot.handle_query(data)
        

def run_socket_server(robot):
    setup_routes(robot)
    socketio.run(app, host='0.0.0.0', port=8080)