import asyncio, serial_asyncio, struct
from . import SerialProtocol, Command
from .. import CommandType


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
        

    def send(self, data: Command):
        # Check if data is a string or pydantic model
        if data.command_type == CommandType.MOTOR:
            packet = struct.pack("<Bhh", 0x01, data.command.left_motor, data.command.right_motor)
            checksum = sum(packet) & 0xFF
            self.protocol.send(packet + bytes([checksum]))
        elif data.command_type == CommandType.LCD:
            if len(data.command.line_1) > 16:
                data.command.line_1 = data.command.line_1[:16]
            if len(data.command.line_2) > 16:
                data.command.line_2 = data.command.line_2[:16]
            
            l1 = data.command.line_1.ljust(16)[:16].encode('utf-8')
            l2 = data.command.line_2.ljust(16)[:16].encode('utf-8')
            
            packet = struct.pack("<B16s16s", 0x02, l1, l2)
            checksum = sum(packet) & 0xFF
            self.protocol.send(packet + bytes([checksum]))
        elif data.command_type == CommandType.SENSOR:
            packet = struct.pack("<B", 0x03)
            checksum = sum(packet) & 0xFF
            self.protocol.send(packet + bytes([checksum]))