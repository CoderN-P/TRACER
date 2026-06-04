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
const float LEFT_CORRECTION_POS = 1.0f;                                         // Correction factor for left motor positive speed (accounts for slight differences in motors/wheels)
const float RIGHT_CORRECTION_POS = 1.0f;                                          // Correction factor for right motor postive speed (accounts for slight differences in motors/wheels)
const float LEFT_CORRECTION_NEG = 1.0f;
const float RIGHT_CORRECTION_NEG = 1.0f;
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

// Feedforward LUTs (3S LiPo)
// Feedforward LUTs (3S LiPo)
const int LOOKUP_TABLE_SIZE = 45;

// Forward Left Calibration Lookup Table
static const CalibrationPoint_t calibration_forward_left[LOOKUP_TABLE_SIZE] = {
    {0.03345335f, 0.14f}, {0.04579700f, 0.16f}, {0.05695682f, 0.18f},
    {0.05729733f, 0.20f}, {0.06730924f, 0.22f}, {0.07847045f, 0.24f},
    {0.08802481f, 0.26f}, {0.09955317f, 0.28f}, {0.12018121f, 0.30f},
    {0.13066354f, 0.32f}, {0.14226667f, 0.34f}, {0.15147210f, 0.36f},
    {0.16396768f, 0.38f}, {0.17429343f, 0.40f}, {0.18421614f, 0.42f},
    {0.19431423f, 0.44f}, {0.20404068f, 0.46f}, {0.21406829f, 0.48f},
    {0.22490705f, 0.50f}, {0.23751819f, 0.52f}, {0.24720492f, 0.54f},
    {0.26064024f, 0.56f}, {0.26541632f, 0.58f}, {0.27896419f, 0.60f},
    {0.28786817f, 0.62f}, {0.30076634f, 0.64f}, {0.30586398f, 0.66f},
    {0.31772303f, 0.68f}, {0.32415169f, 0.70f}, {0.33865162f, 0.72f},
    {0.34933663f, 0.74f}, {0.35997372f, 0.76f}, {0.36900288f, 0.78f},
    {0.37609477f, 0.80f}, {0.38700656f, 0.82f}, {0.39619793f, 0.84f},
    {0.40592269f, 0.86f}, {0.41821264f, 0.88f}, {0.42759426f, 0.90f},
    {0.44094467f, 0.92f}, {0.45088347f, 0.94f}, {0.46344295f, 0.96f},
    {0.47423470f, 0.98f}, {0.48180331f, 1.00f}
};

// Forward Right Calibration Lookup Table
static const CalibrationPoint_t calibration_forward_right[LOOKUP_TABLE_SIZE] = {
    {0.03112455f, 0.14f}, {0.04417064f, 0.16f}, {0.05566319f, 0.18f},
    {0.05689097f, 0.20f}, {0.06797420f, 0.22f}, {0.07806406f, 0.24f},
    {0.08846771f, 0.26f}, {0.09911006f, 0.28f}, {0.12095705f, 0.30f},
    {0.13217687f, 0.32f}, {0.14444629f, 0.34f}, {0.15409516f, 0.36f},
    {0.16577887f, 0.38f}, {0.17684514f, 0.40f}, {0.18765218f, 0.42f},
    {0.19775178f, 0.44f}, {0.20803061f, 0.46f}, {0.21846493f, 0.48f},
    {0.22926844f, 0.50f}, {0.23958710f, 0.52f}, {0.25001533f, 0.54f},
    {0.26115775f, 0.56f}, {0.26877976f, 0.58f}, {0.27804059f, 0.60f},
    {0.28953151f, 0.62f}, {0.29858661f, 0.64f}, {0.30693537f, 0.66f},
    {0.31890525f, 0.68f}, {0.32622058f, 0.70f}, {0.33547456f, 0.72f},
    {0.34368130f, 0.74f}, {0.35220451f, 0.76f}, {0.36094895f, 0.78f},
    {0.37232644f, 0.80f}, {0.38360723f, 0.82f}, {0.39335052f, 0.84f},
    {0.39683487f, 0.86f}, {0.39947346f, 0.88f}, {0.40313708f, 0.90f},
    {0.41304847f, 0.92f}, {0.42095512f, 0.94f}, {0.44729009f, 0.96f},
    {0.45841455f, 0.98f}, {0.46965390f, 1.00f}
};

// Backward Left Calibration Lookup Table
static const CalibrationPoint_t calibration_backward_left[LOOKUP_TABLE_SIZE] = {
    {-0.46729744f, -1.00f}, {-0.43269433f, -0.98f}, {-0.39281530f, -0.96f},
    {-0.38614317f, -0.94f}, {-0.38251776f, -0.92f}, {-0.37960522f, -0.90f},
    {-0.37759715f, -0.88f}, {-0.37402538f, -0.86f}, {-0.37232728f, -0.84f},
    {-0.37060822f, -0.82f}, {-0.36713950f, -0.80f}, {-0.35764717f, -0.78f},
    {-0.33961390f, -0.76f}, {-0.32080621f, -0.74f}, {-0.31407482f, -0.72f},
    {-0.30725245f, -0.70f}, {-0.30126450f, -0.68f}, {-0.29572128f, -0.66f},
    {-0.28711248f, -0.64f}, {-0.27798621f, -0.62f}, {-0.26702752f, -0.60f},
    {-0.25714616f, -0.58f}, {-0.24823026f, -0.56f}, {-0.23839738f, -0.54f},
    {-0.22888455f, -0.52f}, {-0.21824198f, -0.50f}, {-0.20746146f, -0.48f},
    {-0.19732113f, -0.46f}, {-0.18728111f, -0.44f}, {-0.17752323f, -0.42f},
    {-0.16718316f, -0.40f}, {-0.15639547f, -0.38f}, {-0.14695699f, -0.36f},
    {-0.13859137f, -0.34f}, {-0.12655330f, -0.32f}, {-0.11846634f, -0.30f},
    {-0.09651033f, -0.28f}, {-0.08596645f, -0.26f}, {-0.07680778f, -0.24f},
    {-0.06794279f, -0.22f}, {-0.05807680f, -0.18f}, {-0.05788716f, -0.20f},
    {-0.04629174f, -0.16f}, {-0.03376729f, -0.14f}, {-0.01810092f, -0.12f}
};

// Backward Right Calibration Lookup Table
static const CalibrationPoint_t calibration_backward_right[LOOKUP_TABLE_SIZE] = {
    {-0.49416806f, -1.00f}, {-0.47658443f, -0.98f}, {-0.46216390f, -0.96f},
    {-0.45190425f, -0.94f}, {-0.44001174f, -0.92f}, {-0.42999758f, -0.90f},
    {-0.42213993f, -0.88f}, {-0.41259270f, -0.86f}, {-0.40373015f, -0.84f},
    {-0.39665276f, -0.82f}, {-0.38818854f, -0.80f}, {-0.37502843f, -0.78f},
    {-0.36167107f, -0.76f}, {-0.35276491f, -0.74f}, {-0.34280500f, -0.72f},
    {-0.33242556f, -0.70f}, {-0.32247198f, -0.68f}, {-0.31346234f, -0.66f},
    {-0.30311656f, -0.64f}, {-0.29243233f, -0.62f}, {-0.28117101f, -0.60f},
    {-0.27159215f, -0.58f}, {-0.26197363f, -0.56f}, {-0.25047234f, -0.54f},
    {-0.23955181f, -0.52f}, {-0.22984902f, -0.50f}, {-0.21880845f, -0.48f},
    {-0.20848886f, -0.46f}, {-0.19681703f, -0.44f}, {-0.18657865f, -0.42f},
    {-0.17657174f, -0.40f}, {-0.16581689f, -0.38f}, {-0.15534715f, -0.36f},
    {-0.14501687f, -0.34f}, {-0.13456674f, -0.32f}, {-0.12378901f, -0.30f},
    {-0.10127855f, -0.28f}, {-0.09025369f, -0.26f}, {-0.08013279f, -0.24f},
    {-0.06927355f, -0.22f}, {-0.05888958f, -0.18f}, {-0.05851557f, -0.20f},
    {-0.04839759f, -0.16f}, {-0.03620563f, -0.14f}, {-0.01909832f, -0.12f}
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
