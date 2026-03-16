#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// Constants for motor control
const float WHEEL_DIAMETER = 0.05411268; // wheel diameter in meters
const float MAX_PWM = 1.0;               // Max PWM Value (scaled 0-1)
const int REDUCTION_RATIO = 56;
const int MAX_OUTPUT_RPM = 178;
const int ENCODER_PPR = 11;
const int ENCODER_TICKS_PER_REV = ENCODER_PPR * REDUCTION_RATIO * 4;            // Total ticks per wheel revolution with 4x quadrature decoding
const float MAX_OUTPUT_SPEED = (MAX_OUTPUT_RPM / 60.0) * (PI * WHEEL_DIAMETER); // in m/s
const float METERS_PER_TICK = (PI * WHEEL_DIAMETER) / ENCODER_TICKS_PER_REV;    // Distance traveled per encoder tick
const float LEFT_CORRECTION = 1.0;                                              // Correction factor for left motor speed (accounts for slight differences in motors/wheels)
const float RIGHT_CORRECTION = 1.0;                                             // Correction factor for right motor speed (accounts for slight differences in motors/wheels)
const float METERS_PER_TICK_LEFT = METERS_PER_TICK * LEFT_CORRECTION;
const float METERS_PER_TICK_RIGHT = METERS_PER_TICK * RIGHT_CORRECTION;

// Pin definitions
const int EN1 = 26;             // Enable pin for motor 1 - wired
const int IN1 = 18;             // Input pin 1 for motor 1 (right) - wired
const int IN2 = 33;             // Input pin 2 for motor 1 (right) - wired
const int EN2 = 32;             // Enable pin for motor 2 - wired
const int IN3 = 25;             // Input pin 1 for motor 2 (left)  - wired
const int IN4 = 19;             // Input pin 2 for motor 2 (left) - wired
const int IR_FRONT = 4;         // IR sensor at the front
const int IR_BACK = 13;         // IR sensor at the back
const int STBY = 27;            // Standby pin for motor driver - wired
const int BATTERY = 36;         // Battery voltage pin - wired
const int TRIGGER_1 = 15;       // Trigger pin for ultrasonic sensor (PIN TBD)
const int ECHO_1 = 23;          // Echo pin for ultrasonic sensor // Must be interrupt-capable pin (PIN TBD)
const int TRIGGER_2 = 5;        // Trigger pin for second ultrasonic sensor (if used) (PIN TBD)
const int ECHO_2 = 2;           // Echo pin for second ultrasonic sensor (PIN TBD)
const int ENCODER_LEFT_A = 34;  // (yellow wire) Left encoder pin channel A (must be interrupt-capable) - wired
const int ENCODER_LEFT_B = 35;  // (green wire) Left encoder pin channel B (must be interrupt-capable) - wired
const int ENCODER_RIGHT_A = 16; // (yellow) Right encoder pin channel A (must be interrupt-capable) - wired
const int ENCODER_RIGHT_B = 17; // (green) Right encoder pin channel B (must be interrupt-capable) - wired
const int ESTOP_PIN = 14;       // Emergency stop pin (must be interrupt-capable) (PIN TBD)

// NOTE:
// System constants
const int MAX_BUFFER_SIZE = 64;
const int BAUD_RATE = 115200;

// PID + Feedforward constants (for 2S lipo)
const float kS_LEFT = 0.2;
const float kS_RIGHT = 0.1;
const float kV_LEFT = 3.20;  // Velocity feedforward term for left motor (V = kS + kV * velocity)
const float kV_RIGHT = 3.42; // Velocity feedforward term for right motor (V = kS + kV * velocity)
const float kA_LEFT = 0;
const float kA_RIGHT = 0;

const float P_LEFT = 0.0;
const float P_RIGHT = 0.0;
const float I_LEFT = 0.0;
const float I_RIGHT = 0.0;
const float D_LEFT = 0.0;
const float D_RIGHT = 0.0;

// I2C addresses and Register addresses
const int MPU_ADDRESS = 0x68;  // I2C address for MPU6050
const int MAG_ADDRESS = 0x0D;  // I2C address for magnetometer
const int PWR_MGMT_1 = 0x6B;   // Power management register for MPU6050
const int MAG_DATA_REG = 0x00; // Starting register for magnetometer data
const int MAG_CTRL_REG = 0x09; // Control register for magnetometer

// Sensor constants
const float LSB_uT = 0.0244; // ±8G full-scale for magnetometer

// Command definitions
const uint8_t CMD_MOVE = 0x01;
const uint8_t CMD_OLED_UPDATE = 0x02;
const uint8_t CMD_ENABLE = 0x03;
const uint8_t CMD_STOP = 0x04;
const int NUM_TYPES = 4; // Number of command types (MOVE, OLED_UPDATE, ENABLE, STOP)

// Timing intervals (in milliseconds)
const int ULTRASONIC_INTERVAL = 50;   // Sample ultrasonic sensor every 50 ms (20 hz)
const int OLED_UPDATE_INTERVAL = 500; // Update OLED every 500ms
const int MAIN_INTERVAL = 10;         // Run main loop every 10 ms (100 Hz)

// OLED
const int OLED_WIDTH = 128;
const int OLED_HEIGHT = 64;
#endif