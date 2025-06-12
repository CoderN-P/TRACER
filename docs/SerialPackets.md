# Serial Packet Specification

In this project, the communication between the Raspberry Pi and Arduino is done through a serial USB connection. The Arduino sends sensor data to the Raspberry Pi in binary packets, which are then processed and used for various tasks such as navigation and control.
Sensor data is sent from the Arduino to the Raspberry Pi in binary byte backets.

The raspberry Pi also sends commands to the Arduino for controlling motors, LCDs, triggering emergency stops, and purely requesting sensor data.

## Packet Types (Starting Byte)
- 0x01 - Motor Command
- 0x02 - LCD Command
- 0x03 - Requesting Sensor Data
- 0x04 - Emergency Stop
- 0xAA - Sensor Data Packet

## Note on Endianness
All multi-byte values in the packets are in little-endian format, meaning the least significant byte comes first.

### Sensor Data Packet Structure
```
Byte 0: Packet Type (0xAA for sensor data)
Byte 1: Ultrasonic Distance (uint8_t)
Bytes 2-3: IMU Acceleration X (int16_t)
Bytes 4-5: IMU Acceleration Y (int16_t)
Bytes 6-7: IMU Acceleration Z (int16_t)
Bytes 8-9: IMU Gyroscope X (int16_t)
Bytes 10-11: IMU Gyroscope Y (int16_t)
Bytes 12-13: IMU Gyroscope Z (int16_t)
Bytes 14-17: IMU Temperature (float)
Byte 18: IR Flags (uint8_t) (bitmask for IR sensors) 
- bit 0: IR Front (0 = cliff detected, 1 = no cliff)
- bit 1: IR Back (0 = cliff detected, 1 = no cliff)
Byte 19: Battery Level (uint8_t) (0-100%)
Byte 20: Checksum (uint8_t) (simple checksum of all previous bytes)
```

### Motor Command Packet Structure
```
Byte 0: Packet Type (0x01 for motor command)
Bytes 1-2: Left Motor Speed (int16_t) (-255 to 255 PWM value)
Bytes 3-4: Right Motor Speed (int16_t) (-255 to 255 PWM value)
Byte 5: Checksum (uint8_t) (simple checksum of all previous bytes)
```

### LCD Command Packet Structure
```
Byte 0: Packet Type (0x02 for LCD command)
Bytes 1-16: LCD line 1 (char array, 16 bytes, null-terminated)
Bytes 17-32: LCD line 2 (char array, 16 bytes, null-terminated)
Byte 33: Checksum (uint8_t) (simple checksum of all previous bytes)
```

### Emergency Stop Packet Structure
```
Byte 0: Packet Type (0x04 for emergency stop)
Byte 1: Checksum (uint8_t) (simple checksum of all previous bytes)
```

### Request Sensor Data Packet Structure
```
Byte 0: Packet Type (0x03 for requesting sensor data)
Byte 1: Checksum (uint8_t) (simple checksum of all previous bytes)
```

### Checksum Calculation
The checksum is a simple sum of all bytes in the packet modulo 256. It is used to verify the integrity of the packet.


## Example struct code in python

```python
import struct

# Motor Command Example
motor_command = struct.pack(
    '<Bhh',
    0x01,  # Packet Type
    150,   # Left Motor Speed (int16_t)
    -150,  # Right Motor Speed (int16_t)
)

checksum = sum(motor_command[:-1]) & 0xFF  # Calculate checksum (you can also do % 256)
motor_command += bytes([checksum])  # Append checksum byte

# Stop Command Example

stop_command = struct.pack(
    '<B',
    0x04,  # Packet Type
)

checksum = sum(stop_command[:-1]) & 0xFF  # Calculate checksum
stop_command += bytes([checksum])  # Append checksum byte

# Request Sensor Data Example
request_sensor_data = struct.pack(
    '<B',
    0x03,  # Packet Type
)
checksum = sum(request_sensor_data[:-1]) & 0xFF  # Calculate checksum
request_sensor_data += bytes([checksum])  # Append checksum byte

# LCD Command Example
lcd_command = struct.pack(
    '<B16s16s',
    0x02,  # Packet Type
    b'Hello, World!',  # LCD line 1 (padded to 16 bytes)
    b'Line 2 Text',  # LCD line 2 (padded to 16 bytes)
)

checksum = sum(lcd_command[:-1]) & 0xFF  # Calculate checksum (you can also do % 256)
lcd_command += bytes([checksum])  # Append checksum byte

# Sensor Data Example

sensor_data = struct.pack(
    '<BBhhhhhhfBB',
    0xAA,  # Packet Type
    100,  # Ultrasonic Distance
    0, 0, 0,  # IMU Acceleration X, Y, Z
    0, 0, 0,  # IMU Gyroscope X, Y, Z
    25.5,  # IMU Temperature
    0b11,  # IR Flags (both sensors clear)
    85,  # Battery Level
)

checksum = sum(sensor_data[:-1]) & 0xFF  # Calculate checksum
sensor_data += bytes([checksum])  # Append checksum byte
```