import logging

import socketio
from fastapi import FastAPI
import uvicorn

from .models import Command

sio = socketio.AsyncServer(cors_allowed_origins='*', async_mode='asgi')
app = FastAPI()
app = socketio.ASGIApp(sio, other_asgi_app=app)
logger = logging.getLogger("SocketServer")

def setup_routes(robot):
    @sio.on('joystick_input')
    async def on_joystick(sid, data):
        await robot.handle_joystick_input(data)

    @sio.on('query')
    async def on_query(sid, data):
        await robot.handle_query(data["query"])
        
    @sio.on('stop')
    async def on_stop(sid, data):
        await robot.send_safe_command(Command.stop())

    @sio.event
    async def connect(sid, environ):
        logger.info(f"Client connected: {sid}")


async def run_socket_server(robot):
    setup_routes(robot)
    config = uvicorn.Config(app, host="0.0.0.0", port=8080)
    server = uvicorn.Server(config)
    await server.serve()
