#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>
#include "types.h"

// Constants for motor control
const float WHEEL_DIAMETER = 0.05411268; // wheel diameter in meters
const float WHEEL_CIRCUMFERENCE = 0.17;
const float MAX_PWM = 1.0;               // Max PWM Value (scaled 0-1)
const int REDUCTION_RATIO = 56;
const int MAX_OUTPUT_RPM = 178;
const int ENCODER_PPR = 11;
const int ENCODER_TICKS_PER_REV = ENCODER_PPR * REDUCTION_RATIO * 4;            // Total ticks per wheel revolution with 4x quadrature decoding
const float MAX_OUTPUT_SPEED = (MAX_OUTPUT_RPM / 60.0) * WHEEL_CIRCUMFERENCE; // in m/s
const float METERS_PER_TICK = WHEEL_CIRCUMFERENCE / ENCODER_TICKS_PER_REV;    // Distance traveled per encoder tick
const float LEFT_CORRECTION = 0.951f;                                     // Correction factor for left motor speed (accounts for slight differences in motors/wheels)
const float RIGHT_CORRECTION = 1.0f;                                    // Correction factor for right motor speed (accounts for slight differences in motors/wheels)
const float METERS_PER_TICK_LEFT = METERS_PER_TICK * LEFT_CORRECTION;
const float METERS_PER_TICK_RIGHT = METERS_PER_TICK * RIGHT_CORRECTION;

// Pin definitions
const int EN1 = 44;             // Enable pin for motor 1
const int IN1 = 45;             // Input pin 1 for motor 1 (left)
const int IN2 = 46;             // Input pin 2 for motor 1 (left) 
const int EN2 = 43;             // Enable pin for motor 2 
const int IN3 = 47;             // Input pin 1 for motor 2 (right) 
const int IN4 = 48;             // Input pin 2 for motor 2 (right) 
const int STBY = 18;            // Standby pin for motor driver
const int BATTERY = 7;          // Battery voltage pin
const int TRIGGER_1 = 2;        // Trigger pin for ultrasonic sensor 
const int ECHO_1 = 1;           // Echo pin for ultrasonic sensor
const int TRIGGER_2 = 4;        // Trigger pin for second ultrasonic sensor
const int ECHO_2 = 3;           // Echo pin for second ultrasonic sensor
const int ENCODER_LEFT_A = 39;  // (yellow wire) Left encoder pin channel A (must be interrupt-capable) 
const int ENCODER_LEFT_B = 40;  // (green wire) Left encoder pin channel B (must be interrupt-capable)
const int ENCODER_RIGHT_A = 41; // (yellow) Right encoder pin channel A (must be interrupt-capable)
const int ENCODER_RIGHT_B = 42; // (green) Right encoder pin channel B (must be interrupt-capable)
const int ESTOP_PIN = 5;        // Emergency stop pin (must be interrupt-capable) 
const int SERVO_PIN = 6;        // Servo pin for gripper

// System constants
const int MAX_BUFFER_SIZE = 64;
const int BAUD_RATE = 921600;
const uint32_t MAIN_WINDOW_SIZE_MS = 500; // Window size for max loop time calculation in milliseconds

// Feedforward LUTs (3S LiPo)
const int LOOKUP_TABLE_SIZE = 18;
// Forward Left Calibration Lookup Table
static const CalibrationPoint_t calibration_forward_left[LOOKUP_TABLE_SIZE] = {
    {0.03208356f, 0.15000000f}, {0.05985626f, 0.20000000f}, {0.08052401f, 0.25000000f},
    {0.10990567f, 0.30000000f}, {0.12869394f, 0.35000000f}, {0.14624962f, 0.40000000f},
    {0.17565832f, 0.45000000f}, {0.19509651f, 0.50000000f}, {0.22233995f, 0.55000000f},
    {0.25259421f, 0.60000000f}, {0.27213039f, 0.65000000f}, {0.29865987f, 0.70000000f},
    {0.31931582f, 0.75000000f}, {0.34433533f, 0.80000000f}, {0.36373416f, 0.85000000f},
    {0.38855099f, 0.90000000f}, {0.39979501f, 0.95000000f}, {0.43707099f, 1.00000000f}
};

// Forward Right Calibration Lookup Table
static const CalibrationPoint_t calibration_forward_right[LOOKUP_TABLE_SIZE] = {
    {0.03174203f, 0.15000000f}, {0.06142785f, 0.20000000f}, {0.08343488f, 0.25000000f},
    {0.11360916f, 0.30000000f}, {0.13436194f, 0.35000000f}, {0.15450661f, 0.40000000f},
    {0.18288639f, 0.45000000f}, {0.20325819f, 0.50000000f}, {0.23066767f, 0.55000000f},
    {0.26017513f, 0.60000000f}, {0.27893272f, 0.65000000f}, {0.29710146f, 0.70000000f},
    {0.32789273f, 0.75000000f}, {0.34945531f, 0.80000000f}, {0.35449280f, 0.85000000f},
    {0.36922913f, 0.90000000f}, {0.38639564f, 0.95000000f}, {0.44556604f, 1.00000000f}
};

// Backward Left Calibration Lookup Table
static const CalibrationPoint_t calibration_backward_left[LOOKUP_TABLE_SIZE] = {
    {-0.41898294f, -1.00000000f}, {-0.37063282f, -0.95000000f}, {-0.35721870f, -0.90000000f},
    {-0.34070188f, -0.85000000f}, {-0.33017248f, -0.80000000f}, {-0.29560263f, -0.75000000f},
    {-0.28004269f, -0.70000000f}, {-0.25753444f, -0.65000000f}, {-0.24002648f, -0.60000000f},
    {-0.21297467f, -0.55000000f}, {-0.18599313f, -0.50000000f}, {-0.16893043f, -0.45000000f},
    {-0.13981713f, -0.40000000f}, {-0.12353716f, -0.35000000f}, {-0.10560398f, -0.30000000f},
    {-0.07820181f, -0.25000000f}, {-0.06151400f, -0.20000000f}, {-0.03229817f, -0.15000000f}
};

// Backward Right Calibration Lookup Table
static const CalibrationPoint_t calibration_backward_right[LOOKUP_TABLE_SIZE] = {
    {-0.45522107f, -1.00000000f}, {-0.42370881f, -0.95000000f}, {-0.40363799f, -0.90000000f},
    {-0.37371927f, -0.85000000f}, {-0.35464383f, -0.80000000f}, {-0.32856985f, -0.75000000f},
    {-0.30877256f, -0.70000000f}, {-0.27850376f, -0.65000000f}, {-0.26129734f, -0.60000000f},
    {-0.23103248f, -0.55000000f}, {-0.20238560f, -0.50000000f}, {-0.18299967f, -0.44999997f},
    {-0.15258989f, -0.40000000f}, {-0.13395861f, -0.35000000f}, {-0.11372761f, -0.30000000f},
    {-0.08202478f, -0.25000000f}, {-0.06251706f, -0.20000000f}, {-0.03069671f, -0.15000000f}
};


// Constant predefined PID terms;
const float P_LEFT = 1.0;
const float P_RIGHT = 1.0;
const float I_LEFT = 0.0;
const float I_RIGHT = 0.5;
const float D_LEFT = 0.25;
const float D_RIGHT = 0.25;

const float I_ZONE = 0.05; // Error zone for integral control in PID (in m/s, so 5 cm/s)

// I2C addresses and Register addresses
const int LSM_ADDRESS = 0x6B;  // I2C address for LSM6DOS
const int MAG_ADDRESS = 0x0D;  // I2C address for magnetometer
const int LSM_ACCEL_CTRL = 0x10; // Accelerometer control reg on LSM6
const int LSM_GYRO_CTRL = 0x11; // Gyroscope control reg on LSM6
const int LSM_CTRL8_XL = 0x17; // Secondary control register for accelerometer
const int LSM_CTRL7_G = 0x16; // Secondary control register for gyroscope
const int LSM_CTRL3_C = 0x12; // Operating settings control register (Block data update)
const int LSM_PIN_CTRL = 0x02; // Pin CTRL addr for LSM to enable internal pullups on SDO (hardware mistake)
const int LSM_DATA_REG = 0x20; // Starting register for temp + accel + gyro data
const int MAG_DATA_REG = 0x00; // Starting register for magnetometer data
const int MAG_CTRL_REG = 0x09; // Control register for magnetometer

// Sensor constants
const int TOF_TIMING_BUDGET = 70000; // Timing budget for VL53L0X in microseconds (longer timing budget increases accuracy and max range but reduces update rate)

// Command definitions
const uint8_t CMD_MOVE = 0x01;
const uint8_t CMD_PWM = 0x05;
const uint8_t CMD_OLED_UPDATE = 0x02;
const uint8_t CMD_ENABLE = 0x03;
const uint8_t CMD_STOP = 0x04;
const uint8_t CMD_PID = 0x06;
const int NUM_TYPES = 6; // Number of command types (MOVE, OLED_UPDATE, ENABLE, STOP, PWM, PID)

// Timing intervals (in milliseconds)
const int ULTRASONIC_INTERVAL = 50;            // Sample ultrasonic sensor every 50 ms (20 hz)
const int TOF_INTERVAL = 100;                  // Sample time-of-flight sensor every 100 ms (10 Hz)
const int OLED_UPDATE_INTERVAL = 500;          // Update OLED every 500 ms
const int MAIN_INTERVAL = 10;                  // Run main loop every 10 ms (100 Hz)
const uint32_t MOTOR_COMMAND_TIMEOUT_MS = 250; // Stop motors if no motor command arrives within this window

// OLED
const int OLED_WIDTH = 128;
const int OLED_HEIGHT = 64;
#endif
