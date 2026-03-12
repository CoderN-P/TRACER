#include <FreeRTOS/task.h>
#include <FreeRTOS/queue.h>
#include <Wire.h>
#include "PID.h"

#include "driver/mcpwm.h"



// Constants for motor control
const float WHEEL_DIAMETER = 0.05411268; // wheel diameter in meters
const int MAX_PWM = 1; // Max PWM Value (scaled 0-1)
const int REDUCTION_RATIO = 56; 
const int MAX_OUTPUT_RPM = 178;
const int ENCODER_PPR = 11;
const int ENCODER_TICKS_PER_REV = ENCODER_PPR * REDUCTION_RATIO * 4; // Total ticks per wheel revolution
const float MAX_OUTPUT_SPEED = (MAX_OUTPUT_RPM / 60.0) * (PI * WHEEL_DIAMETER); // in m/s
const float METERS_PER_TICK = (PI * WHEEL_DIAMETER) / ENCODER_TICKS_PER_REV; // Distance traveled per encoder tick
const float LEFT_CORRECTION = 1.0; // Correction factor for left motor speed (accounts for slight differences in motors/wheels)
const float RIGHT_CORRECTION = 1.0; // Correction factor for right motor speed (accounts for slight differences in motors/wheels)
const float MAX_OUTPUT_SPEED_LEFT = MAX_OUTPUT_SPEED * LEFT_CORRECTION;
const float MAX_OUTPUT_SPEED_RIGHT = MAX_OUTPUT_SPEED * RIGHT_CORRECTION;
const float METERS_PER_TICK_LEFT = METERS_PER_TICK * LEFT_CORRECTION;
const float METERS_PER_TICK_RIGHT = METERS_PER_TICK * RIGHT_CORRECTION;


// Encoder constants

const int8_t encoder_lut[] = {
    0, -1,  1,  0,  // 00 -> 00, 01, 10, 11
    1,  0,  0, -1,  // 01 -> 00, 01, 10, 11
   -1,  0,  0,  1,  // 10 -> 00, 01, 10, 11
    0,  1, -1,  0   // 11 -> 00, 01, 10, 11
};

// Command queue
QueueHandle_t commandQueue;

// RTOS task handles
TaskHandle_t ultrasonicTaskHandle;
TaskHandle_t mainLoopHandle;
TaskHandle_t serialTaskHandle;
TaskHandle_t commandProcessorHandle;
TaskHandle_t oledUpdateHandle;

// Pin definitions
const int EN1 = 26; // Enable pin for motor 1 - wired
const int IN1 = 18; // Input pin 1 for motor 1  - wired
const int IN2 = 33; // Input pin 2 for motor 1  - wired
const int EN2 = 32; // Enable pin for motor 2 - wired
const int IN3 = 25; // Input pin 1 for motor 2  - wired
const int IN4 = 19; // Input pin 2 for motor 2 - wired
const int IR_FRONT = 8; // IR sensor at the front
const int IR_BACK = 12; // IR sensor at the back
const int STBY = 26; // Standby pin for motor driver - wired
const int BATTERY = A3; // Battery voltage pin
const int TRIGGER_1 = 11; // Trigger pin for ultrasonic sensor
const int ECHO_1 = 5;   // Echo pin for ultrasonic sensor // Must be interrupt-capable pin
const int TRIGGER_2 = 10; // Trigger pin for second ultrasonic sensor (if used)
const int ECHO_2 = 22;   // Echo pin for second ultrasonic sensor (
const int ENCODER_LEFT_A = 16; // Left encoder pin channel A (must be interrupt-capable)
const int ENCODER_LEFT_B = 35; // Left encoder pin channel B (must be interrupt-capable)
const int ENCODER_RIGHT_A = 17; // Right encoder pin channel A (must be interrupt-capable)
const int ENCODER_RIGHT_B = 34; // Right encoder pin channel B (must be interrupt-capable)

// NOTE: 
// System constants
const int MAX_BUFFER_SIZE = 64;
byte cmdBuf[MAX_BUFFER_SIZE];
size_t cmdIdx = 0;
const int BAUD_RATE = 115200;

// PID + Feedforward constants
const float kS_LEFT = 0;
const float kS_RIGHT = 0;
const float kV_LEFT = (1.0 - kS_LEFT)/MAX_OUTPUT_SPEED_LEFT; // Velocity feedforward term for left motor (V = kS + kV * velocity)
const float kV_RIGHT = (1.0 - kS_RIGHT)/MAX_OUTPUT_SPEED_RIGHT; // Velocity feedforward term for right motor (V = kS + kV * velocity)
const float kA_LEFT = 0;
const float kA_RIGHT = 0;

const float P_LEFT = 0.0;
const float P_RIGHT = 0.0;
const float I_LEFT = 0.0;
const float I_RIGHT = 0.0;
const float D_LEFT = 0.0;
const float D_RIGHT = 0.0;

// I2C addresses and Register addresses
const int MPU_ADDRESS = 0x68; // I2C address for MPU6050
const int OLED_ADDRESS = 0x27; // I2C address for OLED
const int MAG_ADDRESS = 0x0D; // I2C address for magnetometer 
const int PWR_MGMT_1 = 0x6B; // Power management register for MPU6050
const int MAG_DATA_REG = 0x00; // Starting register for magnetometer data
const int MAG_CTRL_REG = 0x09; // Control register for magnetometer


// Sensor constants
float LSB_uT = 0.0244; // ±8G full-scale for magnetometer

// Command definitions
const uint8_t CMD_MOVE = 0x01;
const uint8_t CMD_OLED_UPDATE = 0x02;
const uint8_t CMD_ENABLE = 0x03;
const uint8_t CMD_STOP = 0x04;
const int NUM_TYPES = 4; // Number of command types (MOVE, OLED_UPDATE, ENABLE, STOP)

// Timing intervals (in milliseconds)
const unsigned long ULTRASONIC_INTERVAL = 50; // Sample ultrasonic sensor every 50 ms (20 hz)
const unsigned long OLED_UPDATE_INTERVAL = 500; // Update OLED every 500ms
const unsigned long MAIN_INTERVAL = 10; // Run main loop every 10 ms (100 Hz)

bool motorsEnabled = true;
bool motorsRunning = false;

// Sensor data variables
int ax, ay, az, gx, gy, gz;
float magX, magY, magZ;
float lastDistance1, lastDistance2, tempC;
int storedBatteryPercent = -1;
volatile int32_t leftEncoderCount = 0;
volatile int32_t rightEncoderCount = 0;
volatile int32_t lastLeftEncoderCount = 0;
volatile int32_t lastRightEncoderCount = 0;
volatile uint8_t leftPrevAB = 0;
volatile uint8_t rightPrevAB = 0;

volatile unsigned long echoStart1 = 0;
volatile unsigned long echoDuration1 = 0; // Can be negative to indicate errors: -1 = timeout, -2 = too close

volatile unsigned long echoStart2 = 0;
volatile unsigned long echoDuration2 = 0; // Can be negative to indicate errors: -1 = timeout, -2 = too close

static portMUX_TYPE spinlock = portMUX_INITIALIZER_UNLOCKED;

int packetSeq = 0;

// Sensor packet struct

struct SensorPacket {
    uint8_t startByte; // 0xAA
    uint8_t packetSeq; // Incrementing sequence number
    float distance; // Ultrasonic distance in meters
    int16_t ax, ay, az; // Accelerometer data
    int16_t gx, gy, gz; // Gyroscope data
    float tempC; // Temperature in Celsius
    float magX, magY, magZ; // Magnetometer data
    int32_t leftEncoder; // Left wheel encoder count
    int32_t rightEncoder; // Right wheel encoder count
    uint8_t flags; // Bit 0 = front IR, Bit 1 = back IR, Bit 2 = new magnetometer data available
    uint8_t batteryPercent; // Battery voltage percentage (0-100)
    uint32_t timestamp; // Timestamp in microseconds
    uint8_t checksum; // Checksum for data integrity
} __attribute__((packed)); // Packed to avoid padding bytes

// PID Controllers
// Start with only feedforward for tuning
PIDController pidLeft(P_LEFT, I_LEFT, D_LEFT);
PIDController pidRight(P_RIGHT, I_RIGHT, D_RIGHT);

bool initMPU6050()
{
    Wire.beginTransmission(MPU_ADDRESS);
    Wire.write(PWR_MGMT_1); // PWR_MGMT_1 register
    Wire.write(0);    // Wake up the MPU-6050 (0 = wake up)
    byte status = Wire.endTransmission(true);
    return status == 0; // Return true if successful
}

void setup_magnetometer(){
  uint8_t MODE_CONTINUOUS = 0b00000001;
  uint8_t ODR_50Hz = 0b00000100;
  uint8_t LSB_8G = 0b00010000;
  uint8_t OSR_512 = 0x00;
  Wire.beginTransmission(MAG_ADDRESS);
  Wire.write(MAG_CTRL_REG);
  Wire.write(MODE_CONTINUOUS | ODR_50Hz | LSB_8G | OSR_512);
  Wire.endTransmission();
}

void setup_pwm(){
    mcpwm_config_t pwm_config;
    
    pwm_config.frequency = 20000;     // 20 kHz motor PWM
    pwm_config.cmpr_a = 0;            // duty cycle A
    pwm_config.cmpr_b = 0;            // duty cycle B
    pwm_config.counter_mode = MCPWM_UP_COUNTER;
    pwm_config.duty_mode = MCPWM_DUTY_MODE_0;
    
    mcpwm_gpio_init(MCPWM_UNIT_0, MCPWM0A, EN1);
    mcpwm_gpio_init(MCPWM_UNIT_0, MCPWM0B, EN2);
    
    mcpwm_init(MCPWM_UNIT_0, MCPWM_TIMER_0, &pwm_config);
}

void setup()
{
    pinMode(EN1, OUTPUT);
    pinMode(IN1, OUTPUT);
    pinMode(IN2, OUTPUT);
    pinMode(EN2, OUTPUT);
    pinMode(IN3, OUTPUT);
    pinMode(IN4, OUTPUT);
    pinMode(IR_FRONT, INPUT);
    pinMode(IR_BACK, INPUT);
    pinMode(TRIGGER_1, OUTPUT);
    pinMode(TRIGGER_2, OUTPUT);
    pinMode(ECHO_1, INPUT);
    pinMode(ECHO_2, INPUT);
    pinMode(STBY, OUTPUT);
    pinMode(BATTERY, INPUT);
    pinMode(ENCODER_LEFT_A, INPUT_PULLUP);
    pinMode(ENCODER_LEFT_B, INPUT_PULLUP);  
    pinMode(ENCODER_RIGHT_A, INPUT_PULLUP);
    pinMode(ENCODER_RIGHT_B, INPUT_PULLUP);
    
    
    attachInterrupt(digitalPinToInterrupt(ECHO_1), echoISR1, CHANGE);
    attachInterrupt(digitalPinToInterrupt(ECHO_2), echoISR2, CHANGE);
    attachInterrupt(digitalPinToInterrupt(ENCODER_LEFT_A), leftEncoderISR, CHANGE);
    attachInterrupt(digitalPinToInterrupt(ENCODER_LEFT_B), leftEncoderISR, CHANGE);
    attachInterrupt(digitalPinToInterrupt(ENCODER_RIGHT_A), rightEncoderISR, CHANGE);
    attachInterrupt(digitalPinToInterrupt(ENCODER_RIGHT_B), rightEncoderISR, CHANGE);

    Wire.begin();
    Wire.setClock(400000); // Set I2C to 400kHz (Fast Mode)
    Serial.begin(BAUD_RATE);
    Serial.setTimeout(50);

    delay(1000); // Allow time for sensors to stabilize
    digitalWrite(STBY, HIGH);
    
    // Create the command queue (10 commands deep, each command can be up to MAX_BUFFER_SIZE bytes)
    commandQueue = xQueueCreate(10, sizeof(byte) * MAX_BUFFER_SIZE);
    
    // setup_magnetometer();
    setup_pwm();
    
    
    if (initMPU6050())
    {
        // TODO: Add OLED initialization and display something on the screen
        getMPUData(ax, ay, az, gx, gy, gz, tempC);
    }
    else
    {
        // TODO: Display error on OLED
        
    }
    
    // Create RTOS tasks
    
    // Medium priority task for triggering ultrasonic sensors at 20 Hz
    xTaskCreate(ultrasonicTask, "Ultrasonic Task", 2048, NULL, 3, &ultrasonicTaskHandle);
    
    // High priority task for main loop (PID, sensor reading, sending data) at 100 Hz
    xTaskCreate(mainLoop, "Main Loop", 4096, NULL, 4, &mainLoopHandle);
    
    // High priority task for serial listening
    xTaskCreate(vSerialTask, "Serial Task", 2048, NULL, 4, &serialTaskHandle);
    
    // Medium priority task for processing commands from the command queue
    xTaskCreate(commandProcessorTask, "Command Processor Task", 4096, NULL, 3, &commandProcessorHandle);
    
    // Low priority task for updating the OLED at 2 Hz
    xTaskCreate(oledUpdateTask, "OLED Update Task", 2048, NULL, 2, &oledUpdateHandle);
}

uint8_t expectedCommandLength(uint8_t cmd)
{
    if (cmd == CMD_MOVE)
        return 7;
    if (cmd == CMD_OLED_UPDATE)
        return 35;
    if (cmd == CMD_STOP)
        return 3;
    if (cmd == CMD_ENABLE)
        return 3;
    return 0; // invalid
}

uint8_t getIRFront()
{
    return digitalRead(IR_FRONT);
}

uint8_t getIRBack()
{
    return digitalRead(IR_BACK);
}

void leftEncoderISR(){
    lastLeftEncoderCount = leftEncoderCount;
    
    uint8_t currentState = (digitalRead(ENCODER_LEFT_A) << 1) | digitalRead(ENCODER_LEFT_B); // Current state of Left A and B
    uint8_t index = (leftPrevAB << 2) | currentState; // Combine previous and current state to get the index for the lookup table
    leftEncoderCount += encoder_lut[index];
    leftPrevAB = currentState; // Update the previous state to current state for the next interrupt
}

void rightEncoderISR(){
    lastRightEncoderCount = rightEncoderCount;
    
    uint8_t currentState = (digitalRead(ENCODER_RIGHT_A) << 1) | digitalRead(ENCODER_RIGHT_B); // Current state of Right A and B
    uint8_t index = (rightPrevAB << 2) | currentState; // Combine previous and current state to get the index for the lookup table
    rightEncoderCount += encoder_lut[index];
    rightPrevAB = currentState; // Update the previous state to current state for the next interrupt
}

void triggerUltrasonicPulse1()
{
    digitalWrite(TRIGGER_1, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIGGER_1, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIGGER_1, LOW);
}

void triggerUltrasonicPulse2()
{
    digitalWrite(TRIGGER_2, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIGGER_2, HIGH);
    delayMicroseconds(10);  
    digitalWrite(TRIGGER_2, LOW);
}

void getMPUData(int &ax, int &ay, int &az, int &gx, int &gy, int &gz, float &tempC)
{
    Wire.beginTransmission(MPU_ADDRESS);
    Wire.write(0x3B); // Starting register for accelerometer data
    Wire.endTransmission(false);
    Wire.requestFrom(MPU_ADDRESS, 14); // Request 14 bytes (6 for accelerometer, 6 for gyroscope, 2 for temperature)

    if (Wire.available() < 14)
    {
        return;
    }

    // Big endian data: MSB comes first
    ax = (Wire.read() << 8) | Wire.read();
    ay = (Wire.read() << 8) | Wire.read();
    az = (Wire.read() << 8) | Wire.read();

    int16_t tempRaw = (Wire.read() << 8) | Wire.read();
    tempC = tempRaw / 340.0 + 36.53;

    gx = (Wire.read() << 8) | Wire.read();
    gy = (Wire.read() << 8) | Wire.read();
    gz = (Wire.read() << 8) | Wire.read();
}


void getMagnetometerData(float &magX, float &magY, float &magZ)
{
    Wire.beginTransmission(MAG_ADDRESS);
    Wire.write(MAG_DATA_REG); // Starting register for magnetometer data
    Wire.endTransmission(false);
    Wire.requestFrom(MAG_ADDRESS, 6); // Request 6 bytes (2 for each axis)

    if (Wire.available() < 6)
    {
        return;
    }

    uint16_t x_u =  (uint16_t)(Wire.read() | (Wire.read() << 8)); // LSB comes first
    uint16_t y_u =  (uint16_t)(Wire.read() | (Wire.read() << 8));
    uint16_t z_u =  (uint16_t)(Wire.read() | (Wire.read() << 8));

    magX = ((int16_t) x_u) * LSB_uT;
    magY = ((int16_t) y_u) * LSB_uT;
    magZ = ((int16_t) z_u) * LSB_uT;
}

float getLeftMotorSpeed(int32_t left, int32_t lastLeft)
{
    int32_t deltaLeftTicks = left - lastLeft;
    float deltaLeft = deltaLeftTicks * METERS_PER_TICK_LEFT;
    return deltaLeft / (PID_INTERVAL / 1000.0); // Convert to m/s
}

float getRightMotorSpeed(int32_t right, int32_t lastRight)
{
    int32_t deltaRightTicks = right - lastRight;
    float deltaRight = deltaRightTicks * METERS_PER_TICK_RIGHT;
    return deltaRight / (PID_INTERVAL / 1000.0); // Convert to m/s
}


void pidLoop(int32_t left, int32_t lastLeft, int32_t right, int32_t lastRight){
    float leftSpeed = getLeftMotorSpeed(left, lastLeft);
    float rightSpeed = getRightMotorSpeed(right, lastRight);
    
    // Simple feedforward model 
    float leftFeedforward = pidLeft.getSetpoint() * MAX_PWM / MAX_OUTPUT_SPEED_LEFT;
    float rightFeedforward = pidRight.getSetpoint() * MAX_PWM / MAX_OUTPUT_SPEED_RIGHT;
    
    int outputLeft = constrain(pidLeft.compute(leftSpeed, leftFeedforward), -MAX_PWM, MAX_PWM);
    int outputRight = constrain(pidRight.compute(rightSpeed, rightFeedforward), -MAX_PWM, MAX_PWM);
    
    handleMovement(outputLeft, outputRight);
}

void echoISR1() {
    if (digitalRead(ECHO_1) == HIGH) {
        echoStart1 = micros();
    } else {
        echoDuration1 = micros() - echoStart1;
        if (echoDuration1 > 25000) {
            echoDuration1 = -1; // Timeout, no echo received
        } else if (echoDuration1 < 100) {
            echoDuration1 = -2; // Too close, likely noise
        }
    }
}

void echoISR2() {
    if (digitalRead(ECHO_2) == HIGH) {
        echoStart2 = micros();
    } else {
        echoDuration2 = micros() - echoStart2;
        if (echoDuration2 > 25000) {
            echoDuration2 = -1; // Timeout, no echo received
        } else if (echoDuration2 < 100) {
            echoDuration2 = -2; // Too close, likely noise
        }
    }
}

uint8_t getBatteryPercent()
{
    int raw = analogRead(BATTERY);  // 0–4095
    float voltageAtPin = raw * (3.3 / 4095.0);
    float batteryVoltage = voltageAtPin * 13.0 / 3.0; // because of 10k & 3k
    float maxV = 12.6; // 2S LiPo max voltage
    float minV = 9.0; // 3S LiPo min voltage
    
    float percent = (batteryVoltage - minV) / (maxV - minV) * 100.0;
    return constrain((uint8_t)percent, 0, 100);
}

void sendSensorData(int32_t leftEncoder, int32_t rightEncoder, bool newMagData)
{
    // Get ultrasonic data
    uint8_t ir_front = getIRFront();
    uint8_t ir_back = getIRBack();
    uint8_t flags = (ir_front << 0) | (ir_back << 1) | ((int) newMagData << 2); // bit 0 = front, bit 1 = back, bit 2 = new magnetometer data
    uint8_t batteryPercent = 0;
    
    uint32_t now = micros();
    
    if (motorsRunning){
        batteryPercent = storedBatteryPercent; // Use the precomputed battery percentage if motors are on
    } else {
        // Get battery voltage percentage
        if (storedBatteryPercent == -1) {
            batteryPercent = getBatteryPercent(); // Get the battery percentage if not stored
        } else {
            batteryPercent = (uint8_t)(0.2*getBatteryPercent() + 0.8*storedBatteryPercent); // Smooth the battery percentage
        }
        
        storedBatteryPercent = batteryPercent; // Store it for future use
    }

    SensorPacket packet;
    packet.startByte = 0xAA;
    packet.packetSeq = packetSeq++;
    packet.distance = lastDistance1;
    packet.ax = ax;
    packet.ay = ay;
    packet.az = az;
    packet.gx = gx;
    packet.gy = gy;
    packet.gz = gz;
    packet.magX = magX;
    packet.magY = magY;
    packet.magZ = magZ;
    packet.leftEncoder = leftEncoder;
    packet.rightEncoder = rightEncoder;
    packet.tempC = tempC;
    packet.flags = flags;
    packet.batteryPercent = batteryPercent;
    packet.timestamp = now;
    packet.checksum = computeChecksum((uint8_t*)&packet, sizeof(packet)); // Exclude checksum byte
    
    Serial.write((uint8_t*)&packet, sizeof(packet));
}

uint8_t computeChecksum(uint8_t* data, uint8_t len) {
    uint8_t sum = 0;
    for (uint8_t i = 0; i < len; i++) {
        sum += data[i];
    }
    return sum;
}

void handleCommand(byte *buffer, size_t length)
{
    uint8_t cmd = buffer[1]; // Command byte is the second byte (after start byte)

    uint8_t checksum = 0;
    for (size_t i = 0; i < length - 1; i++)
    {
        checksum += buffer[i];
    }
    if (checksum != buffer[length - 1])
    {
        // Checksum error (TODO: Display error on OLED)
        
        return;
    }
    if (cmd == CMD_MOVE && length == 7)
    {
        // Command 0x01: Handle movement
        int16_t leftVel, rightVel; // mm/s
        
        memcpy(&leftVel, &buffer[2], 2);
        memcpy(&rightVel, &buffer[4], 2);
        
        pidLeft.setSetpoint(leftVel / 1000.0f); // Convert mm/s to m/s for PID setpoint
        pidRight.setSetpoint(rightVel / 1000.0f);
        
        // TODO: Update OLED with movement command info
    }
    else if (cmd == CMD_OLED_UPDATE && length == 35)
    {
        // Command 0x02: Update OLED with two lines of text
        // TODO: Update OLED with received text
       
        
    } else if (cmd == CMD_ENABLE && length == 3){
        // Command 0x03: ENABLE
        motorsEnabled = true;
        digitalWrite(STBY, HIGH);
        
        // TODO: Update OLED with enable command info
         
    } else if (cmd == CMD_STOP && length == 3){
      // Command 0x04: STOP
        motorsEnabled = false;
        motorsRunning = false;
        
        pidLeft.reset();
        pidRight.reset();
        
        digitalWrite(STBY, LOW);
        
        // TODO: Update OLED with stop command info
    }
    else
    {
        // Invalid command (TODO: Display error on OLED)
    }
}

int getTypeIndex(uint8_t cmd) {
    switch (cmd) {
        case CMD_MOVE: return 0;
        case CMD_OLED_UPDATE: return 1;
        case CMD_ENABLE: return 2;
        case CMD_STOP: return 3;
        default: return -1; // Invalid command type
    }
}

void handleMovement(int16_t left, int16_t right)
{
    // Values already mapped between -255 and 255
    // Clamp the speeds to the valid range just in case
    
    int16_t leftSpeed = constrain(left, -MAX_PWM, MAX_PWM);
    int16_t rightSpeed = constrain(right, -MAX_PWM, MAX_PWM);
    
    if (!motorsEnabled){
        return; // Ignore movement commands if motors are disabled
    }

    if (leftSpeed > 0)
    {
        digitalWrite(IN1, HIGH);
        digitalWrite(IN2, LOW);
        mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_A, leftSpeed * 100);
    }
    else if (leftSpeed < 0)
    {
        digitalWrite(IN1, LOW);
        digitalWrite(IN2, HIGH);
        mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_A, -leftSpeed * 100);
    }
    else
    {
        digitalWrite(IN1, LOW);
        digitalWrite(IN2, LOW);
        mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_A, 0);
    }

    if (rightSpeed > 0)
    {
        digitalWrite(IN3, HIGH);
        digitalWrite(IN4, LOW);
        mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_B, rightSpeed * 100);
    }
    else if (rightSpeed < 0)
    {
        digitalWrite(IN3, LOW);
        digitalWrite(IN4, HIGH);
        mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_B, -rightSpeed * 100);
    }
    else
    {
        digitalWrite(IN3, LOW);
        digitalWrite(IN4, LOW);
        mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_B, 0);
    }
    
    if (leftSpeed != 0 || rightSpeed != 0){
        motorsRunning = true;
    } else {
        motorsRunning = false;
    }
}

void updateOLED()
{
    // TODO: Implement OLED update logic to display sensor data and system status
    return;
}

// RTOS Tasks

// 1. Ultrasonic trigger loop (20 Hz)

void ultrasonicTask(void *pvParameters) {
    const TickType_t xFrequency = pdMS_TO_TICKS(ULTRASONIC_INTERVAL);
    TickType_t xLastWakeTime = xTaskGetTickCount();
    while (true) {
        vTaskDelayUntil(&xLastWakeTime, xFrequency);
        triggerUltrasonicPulse1();
        
        vTaskDelay(pdMS_TO_TICKS(20)); // Short delay to avoid triggering the second sensor too soon
        
        triggerUltrasonicPulse2();
    }
}

// 2. Main Loop - Handles PID, read IMU, calculate ultrasonic distance, send sensor data at 100 Hz,

void mainLoop(void *pvParameters) {
    const TickType_t xFrequency = pdMS_TO_TICKS(MAIN_INTERVAL);
    TickType_t xLastWakeTime = xTaskGetTickCount();
    
    uint8_t loopCounter = 0;
    
    while (true) {
        vTaskDelayUntil(&xLastWakeTime, xFrequency);
        
        int32_t currentLeftEncoder;
        int32_t currentRightEncoder;
        int32_t lastLeftEncoder;
        int32_t lastRightEncoder;
        long echoDurationCopy1;
        long echoDurationCopy2;
        
        
        taskENTER_CRITICAL(&spinlock);
        {
            currentLeftEncoder = leftEncoderCount;
            currentRightEncoder = rightEncoderCount;
            lastLeftEncoder = lastLeftEncoderCount;
            lastRightEncoder = lastRightEncoderCount;
            echoDurationCopy1 = echoDuration1;
            echoDurationCopy2 = echoDuration2;
        }
        taskEXIT_CRITICAL(&spinlock);
        
        getMPUData(ax, ay, az, gx, gy, gz, tempC);
        
        if (loopCounter % 2 == 0) { // Read magnetometer at 50 Hz
            getMagnetometerData(magX, magY, magZ);
        }
        
        pidLoop(currentLeftEncoder, lastLeftEncoder, currentRightEncoder, lastRightEncoder);
        
        if (echoDurationCopy1 == 0 || echoDurationCopy1 > 25000) {
            lastDistance1 = -1;
        } else if (echoDurationCopy1 < 100) {
            lastDistance1 = -2;
        } else {
            lastDistance1 = (echoDurationCopy1 / 2.0) * 0.0343;
        }
        
        if (echoDurationCopy2 == 0 || echoDurationCopy2 > 25000) {
             lastDistance2 = -1;
        } else if (echoDurationCopy2 < 100) {
            lastDistance2 = -2;
        } else {
            lastDistance2 = (echoDurationCopy2 / 2.0) * 0.0343;
        }
        
        
        sendSensorData(currentLeftEncoder, currentRightEncoder, loopCounter % 2 == 0); // Send magnetometer data every other loop (50 Hz)
    }
}

// 3. Serial listener task - Handles incoming serial data and commands
void vSerialTask(void *pvParameters) {
    const TickType_t xFrequency = pdMS_TO_TICKS(5); // Check for serial data every 5 ms
    TickType_t xLastWakeTime = xTaskGetTickCount();
    
    while (true) {
        vTaskDelayUntil(&xLastWakeTime, xFrequency);
        uint8_t processed = 0;
    
        while (Serial.available() && processed < MAX_BUFFER_SIZE) {
            processed++;
            uint8_t b = Serial.read();
    
            // reset on overflow before writing
            
            if (cmdIdx >= MAX_BUFFER_SIZE) {
                cmdIdx = 0;
            }
    
            // hunt for start byte
            if (cmdIdx == 0 && b != 0xAA) continue;
    
            cmdBuf[cmdIdx++] = b;
    
            // need at least 2 bytes before checking length
            if (cmdIdx < 2) continue;
    
            uint8_t expected = expectedCommandLength(cmdBuf[1]);
    
            // guard against expectedCommandLength returning 0 or 1
            if (expected < 2) {
                cmdIdx = 0;
                continue;
            }
    
            if (cmdIdx == expected) {
                if (xQueueSend(commandQueue, cmdBuf, 0) != pdPASS) {
                    // Queue full, command lost
                    // TODO: Display error on OLED about command queue overflow
                }
                cmdIdx = 0;
            }
        }
    }
}

// 4. Command processor task - Processes commands from the command queue and updates system state accordingly

void commandProcessorTask(void *pvParameters) {
    byte buffer[MAX_BUFFER_SIZE];
    
    static uint8_t latestCmds[NUM_TYPES][MAX_BUFFER_SIZE];
    bool typeReceived[NUM_TYPES];
    
    while (true) {
        if (xQueueReceive(commandQueue, buffer, portMAX_DELAY) == pdPASS) {
            memset(typeReceived, 0, sizeof(typeReceived)); // Reset received flags for all command types
            
             // Update the latest command for this type
             
             do {
                uint8_t type = buffer[1]; // Command byte is the second byte (after start byte)
                
                int typeIndex = getTypeIndex(type); // maps command byte to an index (0 to NUM_TYPES-1)
                
                if (typeIndex != -1) {
                    memcpy(latestCmds[typeIndex], buffer, expectedCommandLength(type));
                    typeReceived[typeIndex] = true; // Mark that we've received a command of this type
                }
                
             } while (xQueueReceive(commandQueue, buffer, 0) == pdPASS); // Keep reading until the queue is empty to get the latest command of each type
             
             
             // Process the latest command of each type, if received
             
             for (int i = 0; i < NUM_TYPES; i++) {
                if (typeReceived[i]) {
                    handleCommand(buffer, expectedCommandLength(buffer[1]));
                }
             }
        }
    }
}

// 5. OLED Update Task - Updates the OLED display at 2 Hz, but only if the content has changed

void oledUpdateTask(void *pvParameters) {
    const TickType_t xFrequency = pdMS_TO_TICKS(OLED_UPDATE_INTERVAL);
    TickType_t xLastWakeTime = xTaskGetTickCount();
    
    while (true) {
        vTaskDelayUntil(&xLastWakeTime, xFrequency);
        
        updateOLED();
    }
}

void loop() {
    // Empty loop since we're using FreeRTOS tasks for everything
}

