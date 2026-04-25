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
const float LEFT_CORRECTION = 0.9646096844;                                     // Correction factor for left motor speed (accounts for slight differences in motors/wheels)
const float RIGHT_CORRECTION = 0.9873417722;                                    // Correction factor for right motor speed (accounts for slight differences in motors/wheels)
const float METERS_PER_TICK_LEFT = METERS_PER_TICK * LEFT_CORRECTION;
const float METERS_PER_TICK_RIGHT = METERS_PER_TICK * RIGHT_CORRECTION;

// Pin definitions
const int EN1 = 43;             // Enable pin for motor 1
const int IN1 = 45;             // Input pin 1 for motor 1 (right)
const int IN2 = 46;             // Input pin 2 for motor 1 (right) 
const int EN2 = 44;             // Enable pin for motor 2 
const int IN3 = 47;             // Input pin 1 for motor 2 (left) 
const int IN4 = 48;             // Input pin 2 for motor 2 (left) 
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

// NOTE:
// System constants
const int MAX_BUFFER_SIZE = 64;
const int BAUD_RATE = 921600;
const uint32_t MAIN_WINDOW_SIZE_MS = 500; // Window size for max loop time calculation in milliseconds

// PID + Feedforward constants (for 2S lipo)
const float kS_LEFT = 0.18;
const float kS_RIGHT = 0.18;
const float kV_LEFT = 3.15;  // Velocity feedforward term for left motor (V = kS + kV * velocity)
const float kV_RIGHT = 3.20; // Velocity feedforward term for right motor (V = kS + kV * velocity)
const float kA_LEFT = 0;
const float kA_RIGHT = 0;

const float P_LEFT = 0.3;
const float P_RIGHT = 0.3;
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
const float LSB_uT = 1.0 / 120.0;    // ±2G full-scale for magnetometer
const int TOF_TIMING_BUDGET = 70000; // Timing budget for VL53L0X in microseconds (longer timing budget increases accuracy and max range but reduces update rate)

// Command definitions
const uint8_t CMD_MOVE = 0x01;
const uint8_t CMD_PWM = 0x05;
const uint8_t CMD_OLED_UPDATE = 0x02;
const uint8_t CMD_ENABLE = 0x03;
const uint8_t CMD_STOP = 0x04;
const int NUM_TYPES = 5; // Number of command types (MOVE, OLED_UPDATE, ENABLE, STOP, PWM)

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
