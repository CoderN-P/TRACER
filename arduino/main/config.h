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
const float LEFT_CORRECTION_POS = 0.97f;                                         // Correction factor for left motor positive speed (accounts for slight differences in motors/wheels)
const float RIGHT_CORRECTION_POS = 1.03f;                                          // Correction factor for right motor postive speed (accounts for slight differences in motors/wheels)
const float LEFT_CORRECTION_NEG = 0.95f;
const float RIGHT_CORRECTION_NEG = 1.03f;
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
const int LOOKUP_TABLE_SIZE = 46;

// Forward Left Calibration Lookup Table
static const CalibrationPoint_t calibration_forward_left[LOOKUP_TABLE_SIZE] = {
    {0.01474517f, 0.10f}, {0.02420882f, 0.12f}, {0.03080842f, 0.14f},
    {0.04075300f, 0.16f}, {0.05138190f, 0.18f}, {0.05143650f, 0.20f},
    {0.05965087f, 0.22f}, {0.06838590f, 0.24f}, {0.07981461f, 0.26f},
    {0.08948494f, 0.28f}, {0.10807378f, 0.30f}, {0.11692877f, 0.32f},
    {0.12632725f, 0.34f}, {0.13611272f, 0.36f}, {0.14622358f, 0.38f},
    {0.15675149f, 0.40f}, {0.16598947f, 0.42f}, {0.17503749f, 0.44f},
    {0.18292905f, 0.46f}, {0.19261316f, 0.48f}, {0.20339590f, 0.50f},
    {0.21318266f, 0.52f}, {0.22322202f, 0.54f}, {0.23275339f, 0.56f},
    {0.24091319f, 0.58f}, {0.25268420f, 0.60f}, {0.25775532f, 0.62f},
    {0.26647816f, 0.64f}, {0.27373869f, 0.66f}, {0.28474573f, 0.68f},
    {0.28984927f, 0.70f}, {0.30330754f, 0.72f}, {0.31172372f, 0.74f},
    {0.31678582f, 0.76f}, {0.32949272f, 0.78f}, {0.33793558f, 0.80f},
    {0.34727236f, 0.82f}, {0.35612964f, 0.84f}, {0.36471212f, 0.86f},
    {0.37597742f, 0.88f}, {0.38447206f, 0.90f}, {0.39598192f, 0.92f},
    {0.40500610f, 0.94f}, {0.41643118f, 0.96f}, {0.42550503f, 0.98f},
    {0.43463966f, 1.00f}
};

// Forward Right Calibration Lookup Table
static const CalibrationPoint_t calibration_forward_right[LOOKUP_TABLE_SIZE] = {
    {0.01530301f, 0.10f}, {0.02542262f, 0.12f}, {0.03303309f, 0.14f},
    {0.04408895f, 0.16f}, {0.05580178f, 0.18f}, {0.05578777f, 0.20f},
    {0.06606990f, 0.22f}, {0.07644531f, 0.24f}, {0.08666648f, 0.26f},
    {0.09760832f, 0.28f}, {0.11745229f, 0.30f}, {0.12820560f, 0.32f},
    {0.13807725f, 0.34f}, {0.14829260f, 0.36f}, {0.15930865f, 0.38f},
    {0.17020778f, 0.40f}, {0.18054716f, 0.42f}, {0.18969242f, 0.44f},
    {0.19935034f, 0.46f}, {0.20917250f, 0.48f}, {0.21916520f, 0.50f},
    {0.22853018f, 0.52f}, {0.23837632f, 0.54f}, {0.24778813f, 0.56f},
    {0.25613401f, 0.58f}, {0.26583435f, 0.60f}, {0.27274246f, 0.62f},
    {0.28157846f, 0.64f}, {0.28939502f, 0.66f}, {0.30172061f, 0.68f},
    {0.30763640f, 0.70f}, {0.31870361f, 0.72f}, {0.32735493f, 0.74f},
    {0.33404065f, 0.76f}, {0.34210820f, 0.78f}, {0.34728623f, 0.80f},
    {0.35868333f, 0.82f}, {0.36652700f, 0.84f}, {0.37411794f, 0.86f},
    {0.39196464f, 0.88f}, {0.39497585f, 0.90f}, {0.39818307f, 0.92f},
    {0.40286250f, 0.94f}, {0.41727322f, 0.96f}, {0.42694603f, 0.98f},
    {0.44770224f, 1.00f}
};

// Backward Left Calibration Lookup Table (Sorted Ascending from -1.0 to -0.1 PWM)
static const CalibrationPoint_t calibration_backward_left[LOOKUP_TABLE_SIZE] = {
    {-0.40617771f, -1.00f}, {-0.36907484f, -0.98f}, {-0.36228472f, -0.96f},
    {-0.35434163f, -0.94f}, {-0.34719237f, -0.92f}, {-0.34282518f, -0.90f},
    {-0.33891615f, -0.88f}, {-0.33556340f, -0.86f}, {-0.33120045f, -0.84f},
    {-0.32391117f, -0.82f}, {-0.31895207f, -0.80f}, {-0.31116258f, -0.78f},
    {-0.29740029f, -0.76f}, {-0.28923218f, -0.74f}, {-0.28345314f, -0.72f},
    {-0.27478638f, -0.70f}, {-0.26647232f, -0.68f}, {-0.25845274f, -0.66f},
    {-0.25023101f, -0.64f}, {-0.24164399f, -0.62f}, {-0.23268724f, -0.60f},
    {-0.22437433f, -0.58f}, {-0.21635577f, -0.56f}, {-0.20731624f, -0.54f},
    {-0.19952078f, -0.52f}, {-0.19014618f, -0.50f}, {-0.18076786f, -0.48f},
    {-0.17236682f, -0.46f}, {-0.16393342f, -0.44f}, {-0.15493187f, -0.42f},
    {-0.14594634f, -0.40f}, {-0.13739010f, -0.38f}, {-0.12869489f, -0.36f},
    {-0.11999980f, -0.34f}, {-0.11094520f, -0.32f}, {-0.10192295f, -0.30f},
    {-0.08492954f, -0.28f}, {-0.07736930f, -0.26f}, {-0.07024384f, -0.24f},
    {-0.06250548f, -0.22f}, {-0.05338336f, -0.20f}, {-0.05344576f, -0.18f},
    {-0.04374849f, -0.16f}, {-0.03370563f, -0.14f}, {-0.02342703f, -0.12f},
    {-0.01350112f, -0.10f}
};

// Backward Right Calibration Lookup Table (Sorted Ascending from -1.0 to -0.1 PWM)
static const CalibrationPoint_t calibration_backward_right[LOOKUP_TABLE_SIZE] = {
    {-0.46549819f, -1.00f}, {-0.45096758f, -0.98f}, {-0.43956072f, -0.96f},
    {-0.42887208f, -0.94f}, {-0.41738443f, -0.92f}, {-0.40688994f, -0.90f},
    {-0.39953093f, -0.88f}, {-0.39124081f, -0.86f}, {-0.38265946f, -0.84f},
    {-0.37408298f, -0.82f}, {-0.36538341f, -0.80f}, {-0.35607876f, -0.78f},
    {-0.34412504f, -0.76f}, {-0.33531682f, -0.74f}, {-0.32671893f, -0.72f},
    {-0.31739326f, -0.70f}, {-0.30807843f, -0.68f}, {-0.29785917f, -0.66f},
    {-0.28757065f, -0.64f}, {-0.27811070f, -0.62f}, {-0.26849299f, -0.60f},
    {-0.25818979f, -0.58f}, {-0.24881550f, -0.56f}, {-0.23966722f, -0.54f},
    {-0.23036346f, -0.52f}, {-0.22080304f, -0.50f}, {-0.21034415f, -0.48f},
    {-0.20112931f, -0.46f}, {-0.19156046f, -0.44f}, {-0.18168770f, -0.42f},
    {-0.17103589f, -0.40f}, {-0.16058454f, -0.38f}, {-0.15030651f, -0.36f},
    {-0.14063112f, -0.34f}, {-0.13031785f, -0.32f}, {-0.11986244f, -0.30f},
    {-0.09853217f, -0.28f}, {-0.08866891f, -0.26f}, {-0.07856898f, -0.24f},
    {-0.06844219f, -0.22f}, {-0.05812690f, -0.20f}, {-0.05837175f, -0.18f},
    {-0.04764512f, -0.16f}, {-0.03753647f, -0.14f}, {-0.02635764f, -0.12f},
    {-0.01573679f, -0.10f}
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
