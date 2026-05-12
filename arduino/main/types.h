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
    float leftSetpoint;
    float rightSetpoint;
    int pidMode; // 0 = PID control mode, 1 = open-loop PWM control mode
    
    int gx, gy, gz;
    int ax, ay, az;
    int magX, magY, magZ;
    int tempC;
    
    float distance1, distance2, distanceFront;
    
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
    float distance_left; // Ultrasonic distance in cm
    float distance_right; // Ultrasonic distance in cm  
    float distance_front; // Time-of-flight distance in cm
    int16_t ax, ay, az; // Accelerometer data
    int16_t gx, gy, gz; // Gyroscope data
    int16_t tempC; // Temperature in Celsius
    int16_t magX, magY, magZ; // Magnetometer data
    int32_t leftEncoder; // Left wheel encoder count
    int32_t rightEncoder; // Right wheel encoder count
    uint8_t flags; // Bit 0 = front IR, Bit 1 = back IR, Bit 2 = new magnetometer data available, Bit 3 = motors enabled
    uint8_t batteryPercent; // Battery voltage percentage (0-100)
    uint32_t timestamp; // Timestamp in microseconds
    uint8_t checksum; // Checksum for data integrity
} __attribute__((packed)); // Packed to avoid padding bytes

#endif