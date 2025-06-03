import asyncio, serial_asyncio
from . import SerialProtocol


class SerialManager:
    def __init__(self, port='/dev/ttyUSB0', baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.transport = None
        self.protocol = None

    async def start(self, robot):
        loop = asyncio.get_running_loop()
        self.transport, self.protocol = await serial_asyncio.create_serial_connection(
            loop, lambda: SerialProtocol(robot), self.port, baudrate=self.baudrate
        )
        

    def send(self, data):
        # Check if data is a string or pydantic model

        if isinstance(data, str):
            # If it's a string, encode it to bytes
            data = data.encode('utf-8')
        elif hasattr(data, 'model_dump_json'):
            # If it's a pydantic model, convert it to JSON and then encode
            data = data.model_dump_json().encode('utf-8')

        self.protocol.send(data + b'\n')