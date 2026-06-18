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

CONSTANTS_SAVE_FILE = (
    Path(__file__).resolve().parents[2]
    / "calibration_files"
    / "constants"
    / "constants.json"
)

def load_persisted_constants():
    if not CONSTANTS_SAVE_FILE.exists():
        return

    try:
        with CONSTANTS_SAVE_FILE.open("r", encoding="utf-8") as fh:
            saved = json.load(fh)

        if not isinstance(saved, dict):
            logger.warning("Ignoring malformed constants file: expected object")
            return

        applied = 0
        for attr, val in saved.items():
            if hasattr(ROBOT_CONFIG, attr):
                try:
                    setattr(ROBOT_CONFIG, attr, val)
                    applied += 1
                except AttributeError:
                    logger.warning(f"Skipped read-only constant '{attr}' from saved file")
        logger.info(f"Loaded {applied} persisted constants from {CONSTANTS_SAVE_FILE}")
    except Exception as exc:
        logger.warning(f"Failed to load persisted constants: {exc}")


def persist_constants():
    try:
        CONSTANTS_SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
        constants = asdict(ROBOT_CONFIG)
        with CONSTANTS_SAVE_FILE.open("w", encoding="utf-8") as fh:
            json.dump(constants, fh, indent=2, sort_keys=True)
        logger.info(f"Persisted constants to {CONSTANTS_SAVE_FILE}")
    except Exception as exc:
        logger.warning(f"Failed to persist constants: {exc}")

def setup_routes(robot):
    load_persisted_constants()

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
        
    @sio.on('set_state') # Manual, path following, LLM control
    async def on_set_state(sid, data):
        await on_robot_loop(robot.set_state(data))
        
    @sio.on('update_constants')
    async def update_constants(sid, data):
        if not isinstance(data, dict):
            logger.warning("Ignoring update_constants payload: expected object")
            return

        save_requested = bool(data.get("save", False))
        constants_payload = {k: v for k, v in data.items() if k != "save"}
        
        embedded_keys = []
        
        for attr, val in constants_payload.items():
            if not hasattr(ROBOT_CONFIG, attr):
                logger.warning(f"Ignoring unknown constant '{attr}'")
                continue
            try:
                if attr in EMBEDDED_CONFIG_KEYS.keys() and val != getattr(ROBOT_CONFIG, attr):
                    embedded_keys.append(attr)
                    
                setattr(ROBOT_CONFIG, attr, val)
                
            except AttributeError:
                logger.warning(f"Ignoring read-only constant '{attr}'")
        
        # Save embedded keys that are diff than their current values
        
        if embedded_keys:
            await on_robot_loop(robot.update_embedded_config({k: constants_payload[k] for k in embedded_keys}))
            
        if save_requested:
            persist_constants()

        logger.info(f"Updated constants: {constants_payload} (save={save_requested})")
        
    @sio.on('vel_command')
    async def vel_command(sid, data):    
        await on_robot_loop(robot.execute_velocity_profile(data["profile"], data["mode"]))
        
    @sio.on('update_virtual_obstacles')
    async def update_virtual_obstacles(sid, data):
        await on_robot_loop(robot.update_virtual_obstacles(data))

    @sio.on('update_obstacle_mode')
    async def update_obstacle_mode(sid, data):
        await on_robot_loop(robot.update_obstacle_mode(data))
        
    @sio.event
    async def connect(sid, environ):
        logger.info(f"Client connected: {sid}")


async def run_socket_server(robot):
    setup_routes(robot)
    config = uvicorn.Config(app, host="0.0.0.0", port=8080, access_log=False)
    server = uvicorn.Server(config)
    await server.serve()
