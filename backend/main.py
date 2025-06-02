from flask import Flask
from flask_socketio import SocketIO
import socketio
from Controller import Controller


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
        
    @sio_client.on('rumble')
    def handle_rumble(data):
        controller.rumble(data['low'], data['high'], data['duration'])
        
    @sio_client.on('sensor_data')
    def handle_sensor_update(data):
        socket.emit('sensor_update', data)

if __name__ == '__main__':
    controller = Controller.initialize(sio_client)
    setup_routes(controller)
    sio_client.connect('http://192.168.4.119:8080')
    socket.run(app, host='0.0.0.0', port=8080)