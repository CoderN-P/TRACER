import logging

import socketio
from fastapi import FastAPI
import uvicorn

from .models import Command

sio = socketio.AsyncServer(cors_allowed_origins='*', async_mode='asgi', logger=False, engineio_logger=False)
app = FastAPI()
app = socketio.ASGIApp(sio, other_asgi_app=app)
logger = logging.getLogger("SocketServer")

def setup_routes(robot):
    async def on_robot_loop(coro):
        return await robot.run_on_robot_loop(coro)

    @sio.on('joystick_input')
    async def on_joystick(sid, data):
        await on_robot_loop(robot.handle_joystick_input(data))

    @sio.on('query')
    async def on_query(sid, data):
        await on_robot_loop(robot.handle_query(data["query"]))
        
    @sio.on('stop')
    async def on_stop(sid, data):
        await on_robot_loop(robot.emergency_stop())
        
    @sio.on('enable')
    async def on_enable(sid, data):
        await on_robot_loop(robot.resume())
        
    @sio.on('lidar')
    async def on_lidar(sid, data):
        await on_robot_loop(robot.process_lidar_data(data))
        
        
    # TODO: Implement the following events: "set_state" (if new state = PATH_FOLLOWING, a path must be provided, "
    @sio.on('set_state') # Manual, path following, LLM control
    async def on_set_state(sid, data):
        await on_robot_loop(robot.set_state(data))
        
    @sio.event
    async def connect(sid, environ):
        logger.info(f"Client connected: {sid}")


async def run_socket_server(robot):
    setup_routes(robot)
    config = uvicorn.Config(app, host="0.0.0.0", port=8080, access_log=False)
    server = uvicorn.Server(config)
    await server.serve()
