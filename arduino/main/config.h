#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>
#include "types.h"

// Constants for motor control
const float WHEEL_DIAMETER = 0.054112680651; // wheel diameter in meters
const float WHEEL_CIRCUMFERENCE = WHEEL_DIAMETER * PI;
const float MAX_PWM = 1.0; // Max PWM Value (scaled 0-1)
const int REDUCTION_RATIO = 56;
const int MAX_OUTPUT_RPM = 167;
const int ENCODER_PPR = 11;
const int ENCODER_TICKS_PER_REV = ENCODER_PPR * REDUCTION_RATIO * 4;          // Total ticks per wheel revolution with 4x quadrature decoding
const float METERS_PER_TICK = WHEEL_CIRCUMFERENCE / ENCODER_TICKS_PER_REV;    // Distance traveled per encoder tick
const float LEFT_CORRECTION_POS = 0.985f;                                         // Correction factor for left motor positive speed (accounts for slight differences in motors/wheels)
const float RIGHT_CORRECTION_POS = 0.988f;                                          // Correction factor for right motor postive speed (accounts for slight differences in motors/wheels)
const float LEFT_CORRECTION_NEG = 0.96f;
const float RIGHT_CORRECTION_NEG = 1.05f;
const float METERS_PER_TICK_LEFT_POS = METERS_PER_TICK * LEFT_CORRECTION_POS;
const float METERS_PER_TICK_RIGHT_POS = METERS_PER_TICK * RIGHT_CORRECTION_POS;
const float METERS_PER_TICK_LEFT_NEG = METERS_PER_TICK * LEFT_CORRECTION_NEG;
const float METERS_PER_TICK_RIGHT_NEG = METERS_PER_TICK * RIGHT_CORRECTION_NEG;

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

// Feedforward LUTs (3S LiPo) - Updated calibration
const int LOOKUP_TABLE_SIZE = 47;

static const CalibrationPoint_t calibration_forward_left[LOOKUP_TABLE_SIZE] = {
    {0.01471551f, 0.08f}, {0.02728582f, 0.10f}, {0.03868969f, 0.12f},
    {0.04937097f, 0.14f}, {0.06025955f, 0.16f}, {0.07090547f, 0.18f},
    {0.07151347f, 0.20f}, {0.08253383f, 0.22f}, {0.09252459f, 0.24f},
    {0.10211609f, 0.26f}, {0.11257267f, 0.28f}, {0.13380598f, 0.30f},
    {0.14356575f, 0.32f}, {0.15408218f, 0.34f}, {0.16442857f, 0.36f},
    {0.17518744f, 0.38f}, {0.18621268f, 0.40f}, {0.19685541f, 0.42f},
    {0.20728335f, 0.44f}, {0.21695011f, 0.46f}, {0.22834330f, 0.48f},
    {0.23834546f, 0.50f}, {0.24803582f, 0.52f}, {0.25873982f, 0.54f},
    {0.26927130f, 0.56f}, {0.27982472f, 0.58f}, {0.29034504f, 0.60f},
    {0.29938670f, 0.62f}, {0.30908101f, 0.64f}, {0.32067824f, 0.66f},
    {0.33247856f, 0.68f}, {0.34383627f, 0.70f}, {0.35439995f, 0.72f},
    {0.36246857f, 0.74f}, {0.37050490f, 0.76f}, {0.37933986f, 0.78f},
    {0.39041755f, 0.80f}, {0.39955450f, 0.82f}, {0.41095062f, 0.84f},
    {0.42389650f, 0.86f}, {0.43536048f, 0.88f}, {0.44813811f, 0.90f},
    {0.45849552f, 0.92f}, {0.46486976f, 0.94f}, {0.47235715f, 0.96f},
    {0.48019753f, 0.98f}, {0.49175886f, 1.00f}
};

// Forward Right Calibration (PWM from 0.08 to 1.0)
static const CalibrationPoint_t calibration_forward_right[LOOKUP_TABLE_SIZE] = {
    {0.01421617f, 0.08f}, {0.02587299f, 0.10f}, {0.03697089f, 0.12f},
    {0.04646026f, 0.14f}, {0.05629570f, 0.16f}, {0.06758575f, 0.18f},
    {0.06768385f, 0.20f}, {0.07843166f, 0.22f}, {0.08882897f, 0.24f},
    {0.09902760f, 0.26f}, {0.10856609f, 0.28f}, {0.12894690f, 0.30f},
    {0.14015794f, 0.32f}, {0.15005988f, 0.34f}, {0.15975725f, 0.36f},
    {0.17004381f, 0.38f}, {0.18008241f, 0.40f}, {0.19068955f, 0.42f},
    {0.20077568f, 0.44f}, {0.21061090f, 0.46f}, {0.22094744f, 0.48f},
    {0.23071272f, 0.50f}, {0.23988400f, 0.52f}, {0.25020799f, 0.54f},
    {0.26022785f, 0.56f}, {0.27051688f, 0.58f}, {0.28065217f, 0.60f},
    {0.29105230f, 0.62f}, {0.30077609f, 0.64f}, {0.31083899f, 0.66f},
    {0.32100865f, 0.68f}, {0.33121733f, 0.70f}, {0.34173904f, 0.72f},
    {0.35180489f, 0.74f}, {0.36068194f, 0.76f}, {0.36931616f, 0.78f},
    {0.37916497f, 0.80f}, {0.38489558f, 0.82f}, {0.39359873f, 0.84f},
    {0.40248865f, 0.86f}, {0.41529259f, 0.88f}, {0.42534421f, 0.90f},
    {0.43400794f, 0.92f}, {0.44149186f, 0.94f}, {0.44887530f, 0.96f},
    {0.45644564f, 0.98f}, {0.46120088f, 1.00f}
};

// Backward Left Calibration (PWM from -1.0 to -0.08)
static const CalibrationPoint_t calibration_backward_left[LOOKUP_TABLE_SIZE] = {
    {-0.45515350f, -1.00f}, {-0.44426344f, -0.98f}, {-0.44143756f, -0.96f},
    {-0.44026240f, -0.94f}, {-0.43307652f, -0.92f}, {-0.42472654f, -0.90f},
    {-0.40457266f, -0.88f}, {-0.39223097f, -0.86f}, {-0.38415098f, -0.84f},
    {-0.37342629f, -0.82f}, {-0.36980169f, -0.80f}, {-0.36203860f, -0.78f},
    {-0.35299378f, -0.76f}, {-0.34412592f, -0.74f}, {-0.33696073f, -0.72f},
    {-0.32708602f, -0.70f}, {-0.31638852f, -0.68f}, {-0.30701211f, -0.66f},
    {-0.29740561f, -0.64f}, {-0.28785534f, -0.62f}, {-0.27855598f, -0.60f},
    {-0.26875051f, -0.58f}, {-0.25819599f, -0.56f}, {-0.24834720f, -0.54f},
    {-0.23934892f, -0.52f}, {-0.22955591f, -0.50f}, {-0.22003570f, -0.48f},
    {-0.20969732f, -0.46f}, {-0.20054787f, -0.44f}, {-0.19007531f, -0.42f},
    {-0.18118057f, -0.40f}, {-0.17067013f, -0.38f}, {-0.16059972f, -0.36f},
    {-0.14864284f, -0.34f}, {-0.13945562f, -0.32f}, {-0.12994250f, -0.30f},
    {-0.10991095f, -0.28f}, {-0.10017442f, -0.26f}, {-0.09028269f, -0.24f},
    {-0.08066321f, -0.22f}, {-0.07101766f, -0.20f}, {-0.07088966f, -0.18f},
    {-0.06111090f, -0.16f}, {-0.05113281f, -0.14f}, {-0.04059797f, -0.12f},
    {-0.02902019f, -0.10f}, {-0.01638360f, -0.08f}
};

// Backward Right Calibration (Padded to 47 points – last point duplicated twice)
static const CalibrationPoint_t calibration_backward_right[LOOKUP_TABLE_SIZE] = {
    {-0.49052175f, -0.96f}, {-0.48106735f, -0.94f}, {-0.46692095f, -0.92f},
    {-0.45612663f, -0.90f}, {-0.44311618f, -0.88f}, {-0.43362916f, -0.86f},
    {-0.42511505f, -0.84f}, {-0.41479366f, -0.82f}, {-0.40736122f, -0.80f},
    {-0.39717210f, -0.78f}, {-0.38688173f, -0.76f}, {-0.37588212f, -0.74f},
    {-0.36519081f, -0.72f}, {-0.35301981f, -0.70f}, {-0.34362824f, -0.68f},
    {-0.33333869f, -0.66f}, {-0.32232497f, -0.64f}, {-0.31180681f, -0.62f},
    {-0.29997335f, -0.60f}, {-0.28968055f, -0.58f}, {-0.27839181f, -0.56f},
    {-0.26855865f, -0.54f}, {-0.25719954f, -0.52f}, {-0.24641852f, -0.50f},
    {-0.23582040f, -0.48f}, {-0.22534596f, -0.46f}, {-0.21483290f, -0.44f},
    {-0.20428182f, -0.42f}, {-0.19288857f, -0.40f}, {-0.18290956f, -0.38f},
    {-0.17132054f, -0.36f}, {-0.16080860f, -0.34f}, {-0.14942116f, -0.32f},
    {-0.13898473f, -0.30f}, {-0.11641998f, -0.28f}, {-0.10555330f, -0.26f},
    {-0.09473465f, -0.24f}, {-0.08428740f, -0.22f}, {-0.07431564f, -0.20f},
    {-0.07424771f, -0.18f}, {-0.06409566f, -0.16f}, {-0.05412010f, -0.14f},
    {-0.04274204f, -0.12f}, {-0.03040476f, -0.10f}, {-0.01676346f, -0.08f},
    {-0.01676346f, -0.08f},  // Pad to 47
    {-0.01676346f, -0.08f}   // Pad to 47
};

// Constant predefined PID terms;
const float P_LEFT = 1.0;
const float P_RIGHT = 1.0;
const float I_LEFT = 0.5;
const float I_RIGHT = 0.5;
const float D_LEFT = 0.5;
const float D_RIGHT = 0.5;

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
