import asyncio
import threading
import serial
import time
import logging
import struct
import serial.tools.list_ports
from .Command import Command
from .CommandTypeEnum import CommandType

class SerialManager:
    def __init__(self, port='/dev/ttyUSB0', baudrate=115200):
        self.serial = serial.Serial(port, baudrate)
        time.sleep(1)  # Allow time for the serial connection to stabilize
        self.running = False
        self.robot = None  # Reference to the robot instance
        self.loop = None   # Event loop to use for coroutine execution
        self._buffer = bytearray()  # Buffer to store incoming data
        self._logger = logging.getLogger("SerialManager")
        self._START_BYTE = 0xAA
        self._PACKET_LENGTH = 24
        
    @staticmethod
    def find_port():
        ports = serial.tools.list_ports.comports()
        for port in ports:
            # Typical Arduino port names on Linux: ttyUSB*, ttyACM*
            # On Windows: COM*
            if 'USB' in port.device or 'ACM' in port.device or 'COM' in port.device:
                if port.manufacturer and 'Arduino' in port.manufacturer:
                    return port.device
                
                return port.device
        return None

    def start(self, robot, loop):
        self.robot = robot
        self.loop = loop
        self.running = True
        thread = threading.Thread(target=self.read_loop, daemon=True)
        thread.start()
        self._logger.info(f"SerialManager started on {self.serial.portstr} at {self.serial.baudrate} baud")
        asyncio.create_task(robot.start())

    def stop(self):
        self.running = False
        self._logger.info("SerialManager stopping...")

    def read_loop(self):
        try:
            while self.running:
                if self.serial.in_waiting:
                    data = self.serial.read(self.serial.in_waiting)
                    self._buffer.extend(data)

                    while len(self._buffer) >= self._PACKET_LENGTH:
                        start_index = self._buffer.find(bytes([self._START_BYTE]))
                        if start_index == -1:
                            self._logger.warning("Start byte not found, clearing buffer")
                            self._buffer.clear()
                            break
                        elif start_index > 0:
                            self._logger.warning(f"Discarding {start_index} bytes before start byte")
                            del self._buffer[:start_index]

                        if len(self._buffer) < self._PACKET_LENGTH:
                            break

                        packet = self._buffer[:self._PACKET_LENGTH]
                        del self._buffer[:self._PACKET_LENGTH]

                        self.loop.call_soon_threadsafe(
                            lambda p=packet: asyncio.create_task(self.robot.process_sensor_data(p))
                        )
                else:
                    time.sleep(0.001)
        except Exception as e:
            self._logger.exception(f"Exception in read_loop: {e}")
            self.running = False

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
