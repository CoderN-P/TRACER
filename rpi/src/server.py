import logging
import json
from pathlib import Path
from dataclasses import asdict

import socketio
from fastapi import FastAPI
import uvicorn

from .models import Command, ROBOT_CONFIG, EMBEDDED_CONFIG_KEYS

sio = socketio.AsyncServer(cors_allowed_origins='*', async_mode='asgi', logger=False, engineio_logger=False)
app = FastAPI()
app = socketio.ASGIApp(sio, other_asgi_app=app)
logger = logging.getLogger("SocketServer")

EVENTS = [
    "joystick_input",
    "query",
    "stop",
    "enable",
    "set_state",
    "update_constants",
    "vel_command",
    "update_virtual_obstacles",
    "update_obstacle_mode"
]
def setup_routes(robot):
    async def on_robot_loop(coro):
        return await robot.run_on_robot_loop(coro)
    
    for event in EVENTS:
        async def handler(sid, data, event=event):
            await robot.socket_manager.process_socketio_command(event, data)
            
        sio.on(event, handler)
            
    @sio.event
    async def connect(sid, environ):
        logger.info(f"Client connected: {sid}")


async def run_socket_server(robot):
    setup_routes(robot)
    config = uvicorn.Config(app, host="0.0.0.0", port=8080, access_log=False)
    server = uvicorn.Server(config)
    await server.serve()
