import asyncio

class SerialProtocol(asyncio.Protocol):
    def __init__(self, robot):
        self.robot = robot
        self.buffer = b''

    def connection_made(self, transport):
        self.transport = transport
        print("[Serial] Connected to Arduino")

    def data_received(self, data: bytes):
        self.buffer += data
        while b'\n' in self.buffer:
            line, self.buffer = self.buffer.split(b'\n', 1)
            decoded = line.decode().stripe
            print(f"[Serial] Received: {decoded}")
            self.robot.process_sensor_data(decoded)

    def send(self, message):
        self.transport.write(message.encode())