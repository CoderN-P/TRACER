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
const float LEFT_CORRECTION_POS = 0.9769f;                                         // Correction factor for left motor positive speed (accounts for slight differences in motors/wheels)
const float RIGHT_CORRECTION_POS = 0.9957f;                                          // Correction factor for right motor postive speed (accounts for slight differences in motors/wheels)
const float LEFT_CORRECTION_NEG = 0.96f;
const float RIGHT_CORRECTION_NEG = 1.06f;
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
    {0.02547820f, 0.10f}, {0.03791647f, 0.12f}, {0.04893042f, 0.14f},
    {0.05925063f, 0.16f}, {0.06991508f, 0.18f}, {0.07005084f, 0.20f},
    {0.08011084f, 0.22f}, {0.09008765f, 0.24f}, {0.10058484f, 0.26f},
    {0.11108293f, 0.28f}, {0.13254161f, 0.30f}, {0.14231500f, 0.32f},
    {0.15268433f, 0.34f}, {0.16238094f, 0.36f}, {0.17378557f, 0.38f},
    {0.18344664f, 0.40f}, {0.19368533f, 0.42f}, {0.20431827f, 0.44f},
    {0.21462681f, 0.46f}, {0.22505853f, 0.48f}, {0.23571994f, 0.50f},
    {0.24560460f, 0.52f}, {0.25594442f, 0.54f}, {0.26608334f, 0.56f},
    {0.27713854f, 0.58f}, {0.28714375f, 0.60f}, {0.29607428f, 0.62f},
    {0.30541743f, 0.64f}, {0.31707708f, 0.66f}, {0.32720329f, 0.68f},
    {0.33893327f, 0.70f}, {0.34928563f, 0.72f}, {0.35791103f, 0.74f},
    {0.36625393f, 0.76f}, {0.37576207f, 0.78f}, {0.38622400f, 0.80f},
    {0.39636876f, 0.82f}, {0.40555890f, 0.84f}, {0.41814509f, 0.86f},
    {0.43138496f, 0.88f}, {0.44160457f, 0.90f}, {0.45372491f, 0.92f},
    {0.46066646f, 0.94f}, {0.46723040f, 0.96f}, {0.47460877f, 0.98f},
    {0.48575821f, 1.00f}
};

// Forward Right Calibration Lookup Table
static const CalibrationPoint_t calibration_forward_right[LOOKUP_TABLE_SIZE] = {
    {0.02377593f, 0.10f}, {0.03518582f, 0.12f}, {0.04617022f, 0.14f},
    {0.05610419f, 0.16f}, {0.06608483f, 0.18f}, {0.06704367f, 0.20f},
    {0.07671429f, 0.22f}, {0.08674303f, 0.24f}, {0.09652219f, 0.26f},
    {0.10711917f, 0.28f}, {0.12735319f, 0.30f}, {0.13789360f, 0.32f},
    {0.14770791f, 0.34f}, {0.15779758f, 0.36f}, {0.16880454f, 0.38f},
    {0.17871641f, 0.40f}, {0.18980674f, 0.42f}, {0.19968454f, 0.44f},
    {0.21056880f, 0.46f}, {0.22010029f, 0.48f}, {0.23076119f, 0.50f},
    {0.24052769f, 0.52f}, {0.25089057f, 0.54f}, {0.26095371f, 0.56f},
    {0.27143494f, 0.58f}, {0.28058072f, 0.60f}, {0.29050018f, 0.62f},
    {0.30070375f, 0.64f}, {0.31218614f, 0.66f}, {0.32154172f, 0.68f},
    {0.33229305f, 0.70f}, {0.34209745f, 0.72f}, {0.35151727f, 0.74f},
    {0.36164841f, 0.76f}, {0.37086429f, 0.78f}, {0.38071175f, 0.80f},
    {0.39063407f, 0.82f}, {0.39817709f, 0.84f}, {0.40781998f, 0.86f},
    {0.41891416f, 0.88f}, {0.42913296f, 0.90f}, {0.43558398f, 0.92f},
    {0.44318785f, 0.94f}, {0.45134707f, 0.96f}, {0.46044603f, 0.98f},
    {0.46946318f, 1.00f}
};

// Backward Left Calibration Lookup Table (Sorted by PWM from -1.0 to -0.08)
static const CalibrationPoint_t calibration_backward_left[LOOKUP_TABLE_SIZE] = {
    {-0.45746466f, -1.00f}, {-0.44947492f, -0.98f}, {-0.44549640f, -0.96f},
    {-0.44219619f, -0.94f}, {-0.43430514f, -0.92f}, {-0.42308308f, -0.90f},
    {-0.40906068f, -0.88f}, {-0.38597180f, -0.86f}, {-0.38317368f, -0.84f},
    {-0.37603682f, -0.82f}, {-0.37140366f, -0.80f}, {-0.36590048f, -0.78f},
    {-0.35683185f, -0.76f}, {-0.34663390f, -0.74f}, {-0.33661534f, -0.72f},
    {-0.32682916f, -0.70f}, {-0.31671937f, -0.68f}, {-0.30563224f, -0.66f},
    {-0.29572419f, -0.64f}, {-0.28571042f, -0.62f}, {-0.27681988f, -0.60f},
    {-0.26685364f, -0.58f}, {-0.25760281f, -0.56f}, {-0.24800810f, -0.54f},
    {-0.23835803f, -0.52f}, {-0.22799290f, -0.50f}, {-0.21835663f, -0.48f},
    {-0.20877119f, -0.46f}, {-0.19855968f, -0.44f}, {-0.18879908f, -0.42f},
    {-0.17848598f, -0.40f}, {-0.16843344f, -0.38f}, {-0.15750345f, -0.36f},
    {-0.14844840f, -0.34f}, {-0.13915846f, -0.32f}, {-0.12906648f, -0.30f},
    {-0.10795129f, -0.28f}, {-0.09880695f, -0.26f}, {-0.08911612f, -0.24f},
    {-0.07905365f, -0.22f}, {-0.06970279f, -0.20f}, {-0.06910393f, -0.18f},
    {-0.05992512f, -0.16f}, {-0.05061906f, -0.14f}, {-0.04056190f, -0.12f},
    {-0.02911636f, -0.10f}
};

// Backward Right Calibration Lookup Table (Sorted by PWM from -0.96 to -0.08)
static const CalibrationPoint_t calibration_backward_right[LOOKUP_TABLE_SIZE] = {
    {-0.49460403f, -0.96f}, {-0.48325670f, -0.94f}, {-0.47170299f, -0.92f},
    {-0.45850999f, -0.90f}, {-0.44787623f, -0.88f}, {-0.43787875f, -0.86f},
    {-0.42775857f, -0.84f}, {-0.42086359f, -0.82f}, {-0.41067541f, -0.80f},
    {-0.40284744f, -0.78f}, {-0.39214075f, -0.76f}, {-0.38040625f, -0.74f},
    {-0.36850798f, -0.72f}, {-0.35693427f, -0.70f}, {-0.34631856f, -0.68f},
    {-0.33495350f, -0.66f}, {-0.32495964f, -0.64f}, {-0.31412172f, -0.62f},
    {-0.30277244f, -0.60f}, {-0.29136808f, -0.58f}, {-0.28035118f, -0.56f},
    {-0.27019494f, -0.54f}, {-0.25814887f, -0.52f}, {-0.24685042f, -0.50f},
    {-0.23646553f, -0.48f}, {-0.22541661f, -0.46f}, {-0.21431658f, -0.44f},
    {-0.20386795f, -0.42f}, {-0.19361500f, -0.40f}, {-0.18265950f, -0.38f},
    {-0.17201259f, -0.36f}, {-0.16044525f, -0.34f}, {-0.14902226f, -0.32f},
    {-0.13806086f, -0.30f}, {-0.11733605f, -0.28f}, {-0.10552829f, -0.26f},
    {-0.09449808f, -0.24f}, {-0.08294588f, -0.22f}, {-0.07228635f, -0.20f},
    {-0.07171101f, -0.18f}, {-0.06117012f, -0.16f}, {-0.05042301f, -0.14f},
    {-0.03971755f, -0.12f}, {-0.02842715f, -0.10f}, {-0.01569815f, -0.08f},
    {-0.01569815f, -0.08f} // duplicate last point to pad array
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
