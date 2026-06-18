#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>
#include "types.h"

// Constants for motor control
const float WHEEL_DIAMETER = 0.054112680651; // wheel diameter in meters
const float WHEEL_CIRCUMFERENCE = WHEEL_DIAMETER * PI;
const float MAX_PWM = 1.0; // Max PWM Value (scaled 0-1)
const int REDUCTION_RATIO = 56;
const int ENCODER_PPR = 11;
const int ENCODER_TICKS_PER_REV = ENCODER_PPR * REDUCTION_RATIO * 4;          // Total ticks per wheel revolution with 4x quadrature decoding
const float METERS_PER_TICK = WHEEL_CIRCUMFERENCE / ENCODER_TICKS_PER_REV;    // Distance traveled per encoder tick

// Default config values (overwritten by rpi)
const float LEFT_CORRECTION_POS = 0.99f;                                         // Correction factor for left motor positive speed (accounts for slight differences in motors/wheels)
const float RIGHT_CORRECTION_POS = 0.984f;                                          // Correction factor for right motor postive speed (accounts for slight differences in motors/wheels)
const float LEFT_CORRECTION_NEG = 0.95f;
const float RIGHT_CORRECTION_NEG = 1.07f;
const float MAX_WHEEL_BASE = 0.26f;
const float MIN_WHEEL_BASE = 0.26f;
const float NOMINAL_WHEEL_BASE = 0.26f;
const bool USE_ADAPTIVE_WHEEL_BASE = true;
const bool USE_GYRO_CORRECTION = true;
const float ALPHA = 3.0f;
const float MAX_LINEAR_VEL_POS = 0.45f;
const float MAX_LINEAR_VEL_NEG = 0.44f;

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


// Feedforward LUTs (3S LiPo) - Corrected MPT factors
const int LOOKUP_TABLE_SIZE = 47;

// Forward Left Calibration (PWM from 0.08 to 1.0)
static const CalibrationPoint_t calibration_forward_left[LOOKUP_TABLE_SIZE] = {
    {0.01140746f, 0.08f}, {0.02650402f, 0.10f}, {0.03784612f, 0.12f},
    {0.04943108f, 0.14f}, {0.05992438f, 0.16f}, {0.07109520f, 0.18f},
    {0.07134030f, 0.20f}, {0.08114395f, 0.22f}, {0.09188510f, 0.24f},
    {0.10178626f, 0.26f}, {0.11349835f, 0.28f}, {0.13553665f, 0.30f},
    {0.14596993f, 0.32f}, {0.15670902f, 0.34f}, {0.16624271f, 0.36f},
    {0.17715822f, 0.38f}, {0.18732969f, 0.40f}, {0.19764032f, 0.42f},
    {0.20843332f, 0.44f}, {0.21749068f, 0.46f}, {0.22870064f, 0.48f},
    {0.23970341f, 0.50f}, {0.25043949f, 0.52f}, {0.26068507f, 0.54f},
    {0.27088596f, 0.56f}, {0.28165083f, 0.58f}, {0.29193682f, 0.60f},
    {0.30157623f, 0.62f}, {0.31106350f, 0.64f}, {0.32164151f, 0.66f},
    {0.33299272f, 0.68f}, {0.34349361f, 0.70f}, {0.35436387f, 0.72f},
    {0.36330507f, 0.74f}, {0.37084556f, 0.76f}, {0.38063054f, 0.78f},
    {0.39016682f, 0.80f}, {0.40021471f, 0.82f}, {0.41242645f, 0.84f},
    {0.42396374f, 0.86f}, {0.43642992f, 0.88f}, {0.44677808f, 0.90f},
    {0.45877846f, 0.92f}, {0.46746051f, 0.94f}, {0.47436628f, 0.96f},
    {0.47932915f, 0.98f}, {0.49271617f, 1.00f}
};

// Forward Right Calibration (PWM from 0.1 to 1.0, missing 0.08 point)
static const CalibrationPoint_t calibration_forward_right[LOOKUP_TABLE_SIZE] = {
    {0.02332981f, 0.10f}, {0.03351987f, 0.12f}, {0.04442490f, 0.14f},
    {0.05492227f, 0.16f}, {0.06598950f, 0.18f}, {0.06579471f, 0.20f},
    {0.07662295f, 0.22f}, {0.08736479f, 0.24f}, {0.09835911f, 0.26f},
    {0.10790126f, 0.28f}, {0.12817762f, 0.30f}, {0.13851050f, 0.32f},
    {0.14861155f, 0.34f}, {0.15879920f, 0.36f}, {0.16866582f, 0.38f},
    {0.17948404f, 0.40f}, {0.18896252f, 0.42f}, {0.20005899f, 0.44f},
    {0.20899501f, 0.46f}, {0.21990325f, 0.48f}, {0.23038805f, 0.50f},
    {0.24018520f, 0.52f}, {0.24959143f, 0.54f}, {0.25861795f, 0.56f},
    {0.26968467f, 0.58f}, {0.28014538f, 0.60f}, {0.28918468f, 0.62f},
    {0.29959581f, 0.64f}, {0.30953461f, 0.66f}, {0.31949746f, 0.68f},
    {0.32891248f, 0.70f}, {0.34025888f, 0.72f}, {0.34927544f, 0.74f},
    {0.35905042f, 0.76f}, {0.36833930f, 0.78f}, {0.37815199f, 0.80f},
    {0.38560573f, 0.82f}, {0.39095664f, 0.84f}, {0.39878931f, 0.86f},
    {0.40787161f, 0.88f}, {0.41774152f, 0.90f}, {0.42965460f, 0.92f},
    {0.44251681f, 0.94f}, {0.45187691f, 0.96f}, {0.45647150f, 0.98f},
    {0.46376051f, 1.00f},
    {0.46376051f, 1.00f}  // Pad to 47
};

// Backward Left Calibration (PWM from -1.0 to -0.08)
static const CalibrationPoint_t calibration_backward_left[LOOKUP_TABLE_SIZE] = {
    {-0.44465495f, -1.00f}, {-0.43871307f, -0.98f}, {-0.43600089f, -0.96f},
    {-0.43265747f, -0.94f}, {-0.42801604f, -0.92f}, {-0.41054496f, -0.90f},
    {-0.39721108f, -0.88f}, {-0.37983292f, -0.86f}, {-0.37187798f, -0.84f},
    {-0.36696903f, -0.82f}, {-0.36104578f, -0.80f}, {-0.35020461f, -0.78f},
    {-0.34417488f, -0.76f}, {-0.33738826f, -0.74f}, {-0.33141106f, -0.72f},
    {-0.32208091f, -0.70f}, {-0.31242254f, -0.68f}, {-0.30123106f, -0.66f},
    {-0.29331340f, -0.64f}, {-0.28456578f, -0.62f}, {-0.27459329f, -0.60f},
    {-0.26479254f, -0.58f}, {-0.25403384f, -0.56f}, {-0.24555285f, -0.54f},
    {-0.23677103f, -0.52f}, {-0.22719838f, -0.50f}, {-0.21825123f, -0.48f},
    {-0.20880971f, -0.46f}, {-0.19842075f, -0.44f}, {-0.18903848f, -0.42f},
    {-0.17826999f, -0.40f}, {-0.16883685f, -0.38f}, {-0.15938455f, -0.36f},
    {-0.14968031f, -0.34f}, {-0.13958810f, -0.32f}, {-0.12988830f, -0.30f},
    {-0.10921639f, -0.28f}, {-0.10025607f, -0.26f}, {-0.08911563f, -0.24f},
    {-0.07920651f, -0.22f}, {-0.06962680f, -0.20f}, {-0.06952495f, -0.18f},
    {-0.05982349f, -0.16f}, {-0.05034328f, -0.14f}, {-0.04021142f, -0.12f},
    {-0.02818852f, -0.10f}, {-0.01421786f, -0.08f}
};

// Backward Right Calibration (Padded to 47 points)
static const CalibrationPoint_t calibration_backward_right[LOOKUP_TABLE_SIZE] = {
    {-0.48793488f, -0.94f}, {-0.47688964f, -0.92f}, {-0.46140869f, -0.90f},
    {-0.45018450f, -0.88f}, {-0.43992352f, -0.86f}, {-0.43100121f, -0.84f},
    {-0.42384369f, -0.82f}, {-0.41523009f, -0.80f}, {-0.40523396f, -0.78f},
    {-0.39560970f, -0.76f}, {-0.38353690f, -0.74f}, {-0.37099094f, -0.72f},
    {-0.36062939f, -0.70f}, {-0.35089231f, -0.68f}, {-0.33950240f, -0.66f},
    {-0.33003201f, -0.64f}, {-0.31859545f, -0.62f}, {-0.30810112f, -0.60f},
    {-0.29459486f, -0.58f}, {-0.28343210f, -0.56f}, {-0.27380766f, -0.54f},
    {-0.26244303f, -0.52f}, {-0.25125783f, -0.50f}, {-0.24033670f, -0.48f},
    {-0.22947639f, -0.46f}, {-0.21814319f, -0.44f}, {-0.20728391f, -0.42f},
    {-0.19593052f, -0.40f}, {-0.18493549f, -0.38f}, {-0.17402943f, -0.36f},
    {-0.16339830f, -0.34f}, {-0.15217598f, -0.32f}, {-0.14110199f, -0.30f},
    {-0.11819175f, -0.28f}, {-0.10625599f, -0.26f}, {-0.09495776f, -0.24f},
    {-0.08412847f, -0.22f}, {-0.07304637f, -0.20f}, {-0.07296877f, -0.18f},
    {-0.06237266f, -0.16f}, {-0.05191586f, -0.14f}, {-0.04079851f, -0.12f},
    {-0.02825013f, -0.10f}, {-0.01406269f, -0.08f},
    {-0.01406269f, -0.08f},  // Pad
    {-0.01406269f, -0.08f}   // Pad to 47
};

// Constant predefined PID terms;
const float P_LEFT = 1.0;
const float P_RIGHT = 1.0;
const float I_LEFT = 0.5;
const float I_RIGHT = 0.5;
const float D_LEFT = 0.5;
const float D_RIGHT = 0.5;
const float I_ZONE = 0.05; // Error zone for integral control in PID (in m/s, so 5 cm/s)
const float OMEGA_P = 0.5;

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

const float LSB_RAD = 8.75 / 1000.0 * PI / 180.0;

// Sensor constants
const int TOF_TIMING_BUDGET = 70000; // Timing budget for VL53L0X in microseconds (longer timing budget increases accuracy and max range but reduces update rate)

// Command definitions
const uint8_t CMD_MOVE = 0x01;
const uint8_t CMD_PWM = 0x05;
const uint8_t CMD_OLED_UPDATE = 0x02;
const uint8_t CMD_ENABLE = 0x03;
const uint8_t CMD_STOP = 0x04;
const uint8_t CMD_CONFIG = 0x06;
const uint8_t CMD_TWIST = 0x07;
const int NUM_TYPES = 7; // Number of command types (MOVE, OLED_UPDATE, ENABLE, STOP, PWM, CONFIG, TWIST)

enum class ConfigReg {
   PID_L_P = 0,
   PID_L_I = 1,
   PID_L_D = 2,
   PID_R_P = 3,
   PID_R_I = 4,
   PID_R_D = 5,
   WHEEL_BASE_MAX = 6,
   WHEEL_BASE_MIN = 7,  
   ALPHA = 8,
   LEFT_CORRECTION_POS = 9,
   RIGHT_CORRECTION_POS = 10,
   LEFT_CORRECTION_NEG = 11,
   RIGHT_CORRECTION_NEG = 12,
   USE_GYRO_CORRECTION = 13,
   USE_ADAPTIVE_WHEEL_BASE = 14,
   NOMINAL_WHEEL_BASE = 15,
   I_ZONE = 16,
   OMEGA_P = 17,
   MAX_LINEAR_VEL_POS = 18,
   MAX_LINEAR_VEL_NEG = 19,
};

struct GeneralConfig {
    float pLeft = P_LEFT;
    float iLeft = I_LEFT;
    float dLeft = D_LEFT;
    float pRight = P_RIGHT;
    float iRight = I_RIGHT;
    float dRight = D_RIGHT;
    float maxWheelBase = MAX_WHEEL_BASE;
    float minWheelBase = MIN_WHEEL_BASE;
    float nominalWheelBase = NOMINAL_WHEEL_BASE;
    float alpha = ALPHA;
    bool useGyroCorrection = USE_GYRO_CORRECTION;
    bool useAdaptiveWheelBase = USE_GYRO_CORRECTION;
    float leftCorrectionPos = LEFT_CORRECTION_POS;
    float rightCorrectionPos = RIGHT_CORRECTION_POS;
    float leftCorrectionNeg = LEFT_CORRECTION_NEG;
    float rightCorrectionNeg = RIGHT_CORRECTION_NEG;
    float iZone = I_ZONE; 
    float omegaP = OMEGA_P;
    float maxLinearVelPos = MAX_LINEAR_VEL_POS;
    float maxLinearVelNeg = MAX_LINEAR_VEL_NEG;
};

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
