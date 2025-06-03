import asyncio

class SerialProtocol(asyncio.Protocol):
    def __init__(self, robot):
        self.robot = robot

    def connection_made(self, transport):
        self.transport = transport
        print("[Serial] Connected to Arduino")

    def data_received(self, data):
        decoded = data.decode().strip()
        print(f"[Serial] Received: {decoded}")
        self.robot.process_sensor_data(decoded)

    def send(self, message):
        self.transport.write(message.encode())