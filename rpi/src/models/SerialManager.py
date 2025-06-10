import asyncio
import threading
import serial
import time
import struct
from .Command import Command
from .CommandTypeEnum import CommandType

class SerialManager:
    def __init__(self, port='/dev/ttyUSB0', baudrate=115200):
        self.serial = serial.Serial(port, baudrate)
        time.sleep(1)  # Allow time for the serial connection to stabilize
        self.running = False
        self.robot = None  # Reference to the robot instance
        self.loop = None   # Event loop to use for coroutine execution
        self._START_BYTE = 0xAA
        self._PACKET_LENGTH = 24

    def start(self, robot, loop):
        self.robot = robot
        self.loop = loop
        self.running = True
        thread = threading.Thread(target=self.read_loop, daemon=True)
        thread.start()
        print(f"SerialManager started on {self.serial.portstr} at {self.serial.baudrate} baud")
        asyncio.create_task(robot.start())

    def read_loop(self):
        while self.running:
            if self.serial.in_waiting >= self._PACKET_LENGTH:
                data = self.serial.read(self._PACKET_LENGTH)
                if data[0] == self._START_BYTE:
                    future = asyncio.run_coroutine_threadsafe(
                        self.robot.process_sensor_data(data), self.loop
                    )
                    try:
                        future.result()  # Optional: block and catch exceptions
                    except Exception as e:
                        print(f"[Serial] Coroutine failed: {e}")

    def send(self, data: Command):
        # Check if data is a string or pydantic model
        if data.command_type == CommandType.MOTOR:
            packet = struct.pack("<Bhh", 0x01, data.command.left_motor, data.command.right_motor)
            checksum = sum(packet) & 0xFF
            self.serial.write(packet + bytes([checksum]))
        elif data.command_type == CommandType.LCD:
            if len(data.command.line_1) > 16:
                data.command.line_1 = data.command.line_1[:16]
            if len(data.command.line_2) > 16:
                data.command.line_2 = data.command.line_2[:16]

            l1 = data.command.line_1.ljust(16)[:16].encode('utf-8')
            l2 = data.command.line_2.ljust(16)[:16].encode('utf-8')

            packet = struct.pack("<B16s16s", 0x02, l1, l2)
            checksum = sum(packet) & 0xFF
            self.serial.write(packet + bytes([checksum]))
        elif data.command_type == CommandType.SENSOR:
            packet = struct.pack("<B", 0x03)
            checksum = sum(packet) & 0xFF
            self.serial.write(packet + bytes([checksum]))
        elif data.command_type == CommandType.STOP:
            packet = struct.pack("<B", 0x04)
            checksum = sum(packet) & 0xFF
            self.serial.write(packet + bytes([checksum]))
