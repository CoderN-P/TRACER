import numpy as np
from pydantic import BaseModel, Field
import logging
import struct
from . import UltrasonicSensor, IMUData, MagnetometerData, TOFData

class SensorData(BaseModel):
    """
    Represents sensor data from the robot.
    """
    ultrasonic: UltrasonicSensor = Field(..., description="Data from the ultrasonic sensor")
    imu: IMUData = Field(..., description="Data from the IMU (Inertial Measurement Unit)")
    tof: TOFData = Field(..., description="Data from the Time-of-Flight sensor")
    magnetometer: MagnetometerData = Field(..., description="Data from the magnetometer")
    left_encoder: int = Field(..., description="Left wheel encoder delta ticks")
    right_encoder: int = Field(..., description="Right wheel encoder delta ticks")
    battery: int = Field(..., description="Battery level in percentage (0-100)")
    timestamp: int = Field(..., description="Timestamp of the sensor data in microseconds since epoch") 
    packet_num: int = Field(..., description="Packet number for tracking sensor data updates")
    motors_enabled: bool = Field(..., description="Whether the motors are currently enabled")
    
    
    @classmethod 
    def from_bytes(cls, data: bytes):
        """Convert bytes to SensorData model."""

        # Look for start byte (0xAA)
        start_byte = data[0]
        if start_byte != 0xAA:
            logger = logging.getLogger("RobotManager")
            logger.error(f"Invalid start byte: {hex(start_byte)}, searching for 0xAA")
            raise ValueError("Invalid start byte")

        # Unpack the data according to the Arduino's sendSensorData format
        # <B    - start byte (0xAA)
        # B     - packet number (uint8_t) 
        # h     - distance_left (int16_t mm)
        # h     - distance_right (int16_t mm)
        # h     - distance_front (int16_t mm)
        # h     - ax (int16_t)
        # h     - ay (int16_t)
        # h     - az (int16_t)
        # h     - gx (int16_t)
        # h     - gy (int16_t)
        # h     - gz (int16_t)
        # h     - tempC (int16_t raw)
        # h     - magnetometer x (int16, raw)
        # h     - magnetometer y (int16, raw)
        # h     - magnetometer z (int16, raw)
        # b     - left encoder delta ticks (int8_t)
        # b     - right encoder delta ticks (int8_t)
        # B     - flags (uint8_t) bit 0: new mag data, bit 1: motors enabled
        # B     - battery percentage (uint8_t)
        # I     - timestamp (uint32_t, microseconds)
        # B     - checksum (uint8_t)

        fields = struct.unpack('<BBhhhhhhhhhhhhhbbBBIB', data)
        start, packet_num, distance_left, distance_right, distance_front, ax, ay, az, gx, gy, gz, temp, mag_x, mag_y, mag_z, left_encoder_ticks, right_encoder_ticks, flags, battery, timestamp, received_checksum = fields

        # Calculate checksum (sum of all bytes except checksum byte)
        calculated_checksum = sum(data[:-1]) & 0xFF
        valid = calculated_checksum == received_checksum

        if not valid:
            logger = logging.getLogger("RobotManager")
            logger.error(f"Invalid checksum: calculated={calculated_checksum}, received={received_checksum}")


        new_mag_data = bool(flags & 0b00000001)
        motors_enabled = bool(flags & 0b00000010)

        mag_heading = MagnetometerData.calculate_heading(mag_x, mag_y, mag_z)

        data = {
            "ultrasonic": {
                "distance_left": distance_left / 10.0,  # Convert from mm to cm
                "distance_right": distance_right / 10.0
            },
            "tof": {
                "distance_front": distance_front / 10.0
            },
            "imu": {
                "acceleration_x": ax * ROBOT_CONFIG.LSB_A ,
                "acceleration_y": ay * ROBOT_CONFIG.LSB_A,
                "acceleration_z": az * ROBOT_CONFIG.LSB_A,
                "gyroscope_x": gx * ROBOT_CONFIG.LSB_RAD,
                "gyroscope_y": gy * ROBOT_CONFIG.LSB_RAD,
                "gyroscope_z": gz * ROBOT_CONFIG.LSB_RAD,
                "temperature": temp * ROBOT_CONFIG.LSB_C + ROBOT_CONFIG.TEMP_OFFSET
            },
            "magnetometer": {
                "x": mag_x * ROBOT_CONFIG.LSB_uT,
                "y": mag_y * ROBOT_CONFIG.LSB_uT,
                "z": mag_z * ROBOT_CONFIG.LSB_uT,
                "heading": mag_heading,
                "new": new_mag_data
            },
            "left_encoder": left_encoder_ticks,
            "right_encoder": right_encoder_ticks,
            "battery": battery,
            "timestamp": timestamp,
            "packet_num": packet_num,
            "motors_enabled": motors_enabled
        }

        return cls.model_validate(data)
    
    @staticmethod
    def clean(x):

        if isinstance(x, dict):
            return {k: SensorData.clean(v) for k, v in x.items()}

        if isinstance(x, (np.floating,)):
             return float(x)

        if isinstance(x, (np.integer,)):
             return int(x)

        return x
