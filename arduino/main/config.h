#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>
#include "types.h"

// Constants for motor control
const float WHEEL_DIAMETER = 0.0545; // wheel diameter in meters
const float WHEEL_CIRCUMFERENCE = WHEEL_DIAMETER * PI;
const float MAX_PWM = 1.0; // Max PWM Value (scaled 0-1)
const int REDUCTION_RATIO = 56;
const int MAX_OUTPUT_RPM = 178;
const int ENCODER_PPR = 11;
const int ENCODER_TICKS_PER_REV = ENCODER_PPR * REDUCTION_RATIO * 4;          // Total ticks per wheel revolution with 4x quadrature decoding
const float MAX_OUTPUT_SPEED = (MAX_OUTPUT_RPM / 60.0) * WHEEL_CIRCUMFERENCE; // in m/s
const float METERS_PER_TICK = WHEEL_CIRCUMFERENCE / ENCODER_TICKS_PER_REV;    // Distance traveled per encoder tick
const float LEFT_CORRECTION = 0.951f;                                         // Correction factor for left motor speed (accounts for slight differences in motors/wheels)
const float RIGHT_CORRECTION = 1.0f;                                          // Correction factor for right motor speed (accounts for slight differences in motors/wheels)
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
const int LOOKUP_TABLE_SIZE = 19;
// Forward Left Calibration Lookup Table
static const CalibrationPoint_t calibration_forward_left[LOOKUP_TABLE_SIZE] = {
    {0.014633837120073621f, 0.10000000f}, {0.04306126279800082f, 0.15000000f}, {0.07777964797510790f, 0.20000000f}, {0.09861351128604466f, 0.25000000f}, {0.12864022569302128f, 0.30000000f}, {0.14843959028949197f, 0.35000000f}, {0.16512986496278437f, 0.40000000f}, {0.18940087818236853f, 0.45000000f}, {0.20715215847552820f, 0.50000000f}, {0.24525851411604588f, 0.55000000f}, {0.27109465428051250f, 0.60000000f}, {0.29239693648157070f, 0.65000000f}, {0.31191400570172660f, 0.70000000f}, {0.33985314829392405f, 0.75000000f}, {0.37034058583028300f, 0.80000000f}, {0.38923311578578723f, 0.85000000f}, {0.42166760416745136f, 0.90000000f}, {0.43597829127603455f, 0.95000000f}, {0.46010174315998040f, 1.00000000f}};

// Forward Right Calibration Lookup Table
static const CalibrationPoint_t calibration_forward_right[LOOKUP_TABLE_SIZE] = {
    {0.016427560355895873f, 0.10000000f}, {0.042957042563983604f, 0.15000000f}, {0.07891080683995470f, 0.20000000f}, {0.09939704278650396f, 0.25000000f}, {0.12937659443180850f, 0.30000000f}, {0.15060991241129731f, 0.35000000f}, {0.16795190069804770f, 0.40000000f}, {0.19382011550651862f, 0.45000000f}, {0.21442750622807713f, 0.50000000f}, {0.25096085228805440f, 0.55000000f}, {0.27452282655176610f, 0.60000000f}, {0.29425890117860570f, 0.65000000f}, {0.31241811839081800f, 0.70000000f}, {0.34204640389776214f, 0.75000000f}, {0.36558999430115200f, 0.80000000f}, {0.37246789980423306f, 0.85000000f}, {0.41534372806145975f, 0.90000000f}, {0.43618209718758216f, 0.95000000f}, {0.46401792551898220f, 1.00000000f}};

// Backward Left Calibration Lookup Table
static const CalibrationPoint_t calibration_backward_left[LOOKUP_TABLE_SIZE] = {
    {-0.43532776081182833f, -1.00000000f}, {-0.42003387289513510f, -0.95000000f}, {-0.41223019476140377f, -0.90000000f}, {-0.36087127130231700f, -0.85000000f}, {-0.33560630167227823f, -0.80000000f}, {-0.32476199446514165f, -0.75000000f}, {-0.31245312683721670f, -0.70000000f}, {-0.28863818252803314f, -0.65000000f}, {-0.26528455031763476f, -0.60000000f}, {-0.24408070281922590f, -0.55000000f}, {-0.20980580782073788f, -0.50000000f}, {-0.19021080292974488f, -0.45000000f}, {-0.16528049415329213f, -0.40000000f}, {-0.14670064210577854f, -0.35000000f}, {-0.12708060315369923f, -0.30000000f}, {-0.09825626742664742f, -0.25000000f}, {-0.07896991077585662f, -0.20000000f}, {-0.047119426134519166f, -0.15000000f}, {-0.02299660941067341f, -0.10000000f}};

// Backward Right Calibration Lookup Table
static const CalibrationPoint_t calibration_backward_right[LOOKUP_TABLE_SIZE] = {
    {-0.48535581393331045f, -1.00000000f}, {-0.45557367993437300f, -0.95000000f}, {-0.43849808885553820f, -0.90000000f}, {-0.40332904098863914f, -0.85000000f}, {-0.38119120874356820f, -0.80000000f}, {-0.35614710286656860f, -0.75000000f}, {-0.33558763672758074f, -0.70000000f}, {-0.30552133079738440f, -0.65000000f}, {-0.28248826223804030f, -0.60000000f}, {-0.25592844137721293f, -0.55000000f}, {-0.21950702003191800f, -0.50000000f}, {-0.19848719955102376f, -0.45000000f}, {-0.17383117915924434f, -0.40000000f}, {-0.15321963323726376f, -0.35000000f}, {-0.13224148846902720f, -0.30000000f}, {-0.10272949011113569f, -0.25000000f}, {-0.08120197742286568f, -0.20000000f}, {-0.047224172261098304f, -0.15000000f}, {-0.022654980629270006f, -0.10000000f}};

// Constant predefined PID terms;
const float P_LEFT = 1.0;
const float P_RIGHT = 1.0;
const float I_LEFT = 0.0;
const float I_RIGHT = 0.5;
const float D_LEFT = 0.25;
const float D_RIGHT = 0.25;

const float I_ZONE = 0.05; // Error zone for integral control in PID (in m/s, so 5 cm/s)

// I2C addresses and Register addresses
const int LSM_ADDRESS = 0x6B;    // I2C address for LSM6DOS
const int MAG_ADDRESS = 0x0D;    // I2C address for magnetometer
const int LSM_ACCEL_CTRL = 0x10; // Accelerometer control reg on LSM6
const int LSM_GYRO_CTRL = 0x11;  // Gyroscope control reg on LSM6
const int LSM_CTRL8_XL = 0x17;   // Secondary control register for accelerometer
const int LSM_CTRL7_G = 0x16;    // Secondary control register for gyroscope
const int LSM_CTRL3_C = 0x12;    // Operating settings control register (Block data update)
const int LSM_PIN_CTRL = 0x02;   // Pin CTRL addr for LSM to enable internal pullups on SDO (hardware mistake)
const int LSM_DATA_REG = 0x20;   // Starting register for temp + accel + gyro data
const int MAG_DATA_REG = 0x00;   // Starting register for magnetometer data
const int MAG_CTRL_REG = 0x09;   // Control register for magnetometer

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
const int MAIN_INTERVAL = 5;                   // Run main loop every 5 ms (200 Hz)
const uint32_t MOTOR_COMMAND_TIMEOUT_MS = 250; // Stop motors if no motor command arrives within this window

// OLED
const int OLED_WIDTH = 128;
const int OLED_HEIGHT = 64;
#endif
