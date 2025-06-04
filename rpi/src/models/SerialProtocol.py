import asyncio

class SerialProtocol(asyncio.BufferedProtocol):
    def __init__(self, robot):
        self.robot = robot
        self.buffer = bytearray(1024)
        self.write_offset = 0

    def connection_made(self, transport):
        self.transport = transport
        print("[Serial] Connected to Arduino")

    def get_buffer(self, sizehint):
        return memoryview(self.buffer)[self.write_offset:]

    def buffer_updated(self, nbytes):
        self.write_offset += nbytes
        
        while self.write_offset >= 23:
            packet = self.buffer[:23]
            asyncio.create_task(self.robot.process_sensor_data(packet))
            # Shift remaining data
            self.buffer[:self.write_offset - 23] = self.buffer[23:self.write_offset]
            self.write_offset -= 23

    def send(self, message: bytes):
        self.transport.write(message)