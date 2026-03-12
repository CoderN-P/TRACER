#ifndef TYPES_H
#define TYPES_H

// Robot State struct
struct RobotState {
    int32_t leftEncoder;
    int32_t rightEncoder;
    
    float leftPWM;
    float rightPWM;
    float leftSpeed;
    float rightSpeed;
    
    int gx, gy, gz;
    int ax, ay, az;
    float magX, magY, magZ;
    float tempC;
    
    float distance1, distance2;
    
    uint8_t irFront;
    uint8_t irBack;
    
    float mainLoopElapsedMs;
    uint8_t batteryPercent;
    uint32_t timestamp;
    bool newMagData;
    
    char oledLine1[17]; // 16 chars + null terminator
    char oledLine2[17]; // 16 chars + null terminator
}; 

// Sensor packet struct
struct SensorPacket {
    uint8_t startByte; // 0xAA
    uint8_t packetSeq; // Incrementing sequence number
    float distance; // Ultrasonic distance in meters
    int16_t ax, ay, az; // Accelerometer data
    int16_t gx, gy, gz; // Gyroscope data
    float tempC; // Temperature in Celsius
    float magX, magY, magZ; // Magnetometer data
    int32_t leftEncoder; // Left wheel encoder count
    int32_t rightEncoder; // Right wheel encoder count
    uint8_t flags; // Bit 0 = front IR, Bit 1 = back IR, Bit 2 = new magnetometer data available, Bit 3 = motors enabled
    uint8_t batteryPercent; // Battery voltage percentage (0-100)
    uint32_t timestamp; // Timestamp in microseconds
    uint8_t checksum; // Checksum for data integrity
} __attribute__((packed)); // Packed to avoid padding bytes

#endif