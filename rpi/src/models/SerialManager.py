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
        self._PACKET_LENGTH = 57  # Start byte (1) + Sensor data (55) + Checksum (1)
        
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
        
    def start_read(self, callback=None):
        self.running = True
        thread = threading.Thread(target=self.read_loop, args=(callback,), daemon=True)
        thread.start()
        self._logger.info("SerialManager read loop started")

    def stop(self):
        self.running = False
        self._logger.info("SerialManager stopping...")

    def read_loop(self, callback=None):
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

                        packet = bytes(self._buffer[:self._PACKET_LENGTH])
                        del self._buffer[:self._PACKET_LENGTH]
                        
                        if not callback:
                            asyncio.run_coroutine_threadsafe(self.robot.process_sensor_data(bytes(packet)), self.loop)
                        else:
                            callback(bytes(packet))
                else:
                    time.sleep(0.001)
        except Exception as e:
            self._logger.exception(f"Exception in read_loop: {e}")
            self.running = False

    def send(self, data: Command):
        # Check if data is a string or pydantic model
        if data.command_type == CommandType.MOTOR:
            left = max(-32767, min(32767, int(data.command.left_motor * 1000))) # Convert from m/s to mm/s to fit in int16
            right = max(-32767, min(32767, int(data.command.right_motor * 1000))) # Convert from m/s to mm/s to fit in int16
            packet = struct.pack("<Bhh", 0x01, left, right)
            full = bytes([0xAA]) + packet
            checksum = sum(full) & 0xFF
            self.serial.write(full + bytes([checksum]))
        elif data.command_type == CommandType.LCD:
            if len(data.command.line_1) > 16:
                data.command.line_1 = data.command.line_1[:16]
            if len(data.command.line_2) > 16:
                data.command.line_2 = data.command.line_2[:16]

            l1 = data.command.line_1.ljust(16)[:16].encode('utf-8')
            l2 = data.command.line_2.ljust(16)[:16].encode('utf-8')

            packet = struct.pack("<B16s16s", 0x02, l1, l2)
            full = bytes([0xAA]) + packet
            checksum = sum(full) & 0xFF
            self.serial.write(full + bytes([checksum]))
        elif data.command_type == CommandType.ENABLE:
            packet = struct.pack("<B", 0x03)
            full = bytes([0xAA]) + packet
            checksum = sum(full) & 0xFF
            self.serial.write(full + bytes([checksum]))
        elif data.command_type == CommandType.STOP:
            packet = struct.pack("<B", 0x04)
            full = bytes([0xAA]) + packet
            checksum = sum(full) & 0xFF
            self.serial.write(full + bytes([checksum]))
        elif data.command_type == CommandType.PWM:
            left = max(-1000, min(1000, int(1000*data.command.left_motor)))
            right = max(-1000, min(1000, int(1000*data.command.right_motor)))
            
            packet = struct.pack("<Bhh", 0x05, left, right)
            full = bytes([0xAA]) + packet
            checksum = sum(full) & 0xFF
            self.serial.write(full + bytes([checksum]))
        else:
            self._logger.warning(f"Unknown command type: {data.command_type}")
                                     
                                     
