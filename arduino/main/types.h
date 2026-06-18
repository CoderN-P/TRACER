#ifndef TYPES_H
#define TYPES_H
#include <cstdint>

typedef struct {
    float input;   // Measured Value
    float output;  // Target Command
} CalibrationPoint_t;

// Robot State struct
struct RobotState {
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
    
    int16_t distance1, distance2, distanceFront;
    
    float mainLoopElapsedMs;
    uint8_t batteryPercent;
    uint32_t timestamp;
    bool newMagData;
    
    char oledLine1[17]; // 16 chars + null terminator
    char oledLine2[17]; // 16 chars + null terminator
}; 

struct GeneralConfig {
    float pLeft, iLeft, dLeft;
    float pRight, iRight, dRight;
    float maxWheelBase, minWheelBase, nominalWheelBase;
    float alpha;
    bool useGyroCorrection, useAdaptiveWheelBase;
    float leftCorrectionPos, rightCorrectionPos, leftCorrectionNeg, rightCorrectionNeg;
    float iZone;
}

// Sensor packet struct
struct SensorPacket {
    uint8_t startByte; // 0xAA
    uint8_t packetSeq; // Incrementing sequence number
    int16_t distance_left; // Ultrasonic distance in cm
    int16_t distance_right; // Ultrasonic distance in cm  
    int16_t distance_front; // Time-of-flight distance in cm
    int16_t ax, ay, az; // Accelerometer data
    int16_t gx, gy, gz; // Gyroscope data
    int16_t tempC; // Temperature in Celsius
    int16_t magX, magY, magZ; // Magnetometer data
    int8_t leftEncoder; // Left wheel encoder count
    int8_t rightEncoder; // Right wheel encoder count
    uint8_t flags; // Bit 0 = front IR, Bit 1 = back IR, Bit 2 = new magnetometer data available, Bit 3 = motors enabled
    uint8_t batteryPercent; // Battery voltage percentage (0-100)
    uint32_t timestamp; // Timestamp in microseconds
    uint8_t checksum; // Checksum for data integrity
} __attribute__((packed)); // Packed to avoid padding bytes

#endif