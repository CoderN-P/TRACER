#include <LiquidCrystal_I2C.h>
#include <Wire.h>
#include <PulseInput.h>   
#include "PID.h"


// Constants for motor control
const float WHEEL_DIAMETER = 0.05411268; // wheel diameter in meters
const int MIN_PWM = 50; // Minimum PWM value
const int MAX_PWM = 255; // Max PWM Value
const int REDUCTION_RATIO = 56;
const int MAX_OUTPUT_RPM = 178;

// Encoder constants
const int ENCODER_PPR = 11;
const int ENCODER_TICKS_PER_REV = ENCODER_PPR * REDUCTION_RATIO * 4; // Total ticks per wheel revolution
const int8_t encoder_lut[] = {
    0, -1,  1,  0,  // 00 -> 00, 01, 10, 11
    1,  0,  0, -1,  // 01 -> 00, 01, 10, 11
   -1,  0,  0,  1,  // 10 -> 00, 01, 10, 11
    0,  1, -1,  0   // 11 -> 00, 01, 10, 11
};

// Pin definitions
const int EN1 = 9; // Enable pin for motor 1
const int IN1 = 3; // Input pin 1 for motor 1
const int IN2 = 4; // Input pin 2 for motor 1
const int EN2 = 5; // Enable pin for motor 2
const int IN3 = 6; // Input pin 1 for motor 2
const int IN4 = 7; // Input pin 2 for motor 2
const int IR_FRONT = 8; // IR sensor at the front
const int IR_BACK = 12; // IR sensor at the back
const int STBY = 13; // Standby pin for motor driver
const int BATTERY = A3; // Battery voltage pin
const int TRIGGER = 11; // Trigger pin for ultrasonic sensor
const int ECHO = 2;   // Echo pin for ultrasonic sensor // Must be interrupt-capable pin
const int ENCODER_LEFT_A = 18; // Left encoder pin channel A (must be interrupt-capable)
const int ENCODER_LEFT_B = 19; // Left encoder pin channel B (must be interrupt-capable)
const int ENCODER_RIGHT_A = 20; // Right encoder pin channel A (must be interrupt-capable)
const int ENCODER_RIGHT_B = 21; // Right encoder pin channel B (must be interrupt-capable)

// System constants
const int MAX_BUFFER_SIZE = 64;
byte cmdBuf[MAX_BUFFER_SIZE];
size_t cmdIdx = 0;
const int BAUD_RATE = 115200;



// I2C addresses and Register addresses
const int MPU_ADDRESS = 0x68; // I2C address for MPU6050
const int LCD_ADDRESS = 0x27; // I2C address for LCD
const int PWR_MGMT_1 = 0x6B; // Power management register for MPU6050

// Command definitions
const uint8_t CMD_MOVE = 0x01;
const uint8_t CMD_LCD_UPDATE = 0x02;
const uint8_t CMD_ENABLE = 0x03;
const uint8_t CMD_STOP = 0x04;

// Timing intervals (in milliseconds)
const unsigned long ULTRASONIC_INTERVAL = 50; // Sample ultrasonic sensor every 50 ms (20 hz)
const unsigned long LCD_UPDATE_INTERVAL = 500; // Update LCD every 500ms

// Timing variables
unsigned long lastUltrasonicSampleTime = 0;
unsigned long lastLCDUpdateTime = 0;
unsigned long lastPIDComputeTime = 0;

bool motorsEnabled = true;
bool motorsRunning = false;

// Sensor data variables
int ax, ay, az, gx, gy, gz;
float lastDistance, tempC;
int storedBatteryPercent = -1;
volatile int32_t leftEncoderCount = 0;
volatile int32_t rightEncoderCount = 0;
volatile int32_t lastLeftEncoderCount = 0;
volatile int32_t lastRightEncoderCount = 0;
volatile unsigned int8_t leftPrevAB = 0;
volatile unsigned int8_t rightPrevAB = 0;
volatile unsigned long echoStart = 0;
volatile unsigned long echoDuration = 0; // Can be negative to indicate errors: -1 = timeout, -2 = too close
volatile bool echoReady = false;
int packetSeq = 0;

// LCD Display buffers
char lastLine1[17] = "";
char lastLine2[17] = "";
char lcdLine1[17] = "Init...";
char lcdLine2[17] = "";
LiquidCrystal_I2C lcd(LCD_ADDRESS, 16, 2);

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

PIDController pidLeft(1.0, 0.0, 0.1, 100);
PIDController pidRight(1.0, 0.0, 0.1, 100);

bool initMPU6050()
{
    Wire.beginTransmission(MPU_ADDRESS);
    Wire.write(PWR_MGMT_1); // PWR_MGMT_1 register
    Wire.write(0);    // Wake up the MPU-6050 (0 = wake up)
    byte status = Wire.endTransmission(true);
    return status == 0; // Return true if successful
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
    pinMode(TRIGGER, OUTPUT);
    pinMode(ECHO, INPUT);
    pinMode(STBY, OUTPUT);
    pinMode(BATTERY, INPUT);
    
    attachInterrupt(digitalPinToInterrupt(ECHO), echoISR, CHANGE);
    attachInterrupt(digitalPinToInterrupt(ENCODER_LEFT_A), leftEncoderISR, CHANGE);
    attachInterrupt(digitalPinToInterrupt(ENCODER_LEFT_B), leftEncoderISR, CHANGE);
    attachInterrupt(digitalPinToInterrupt(ENCODER_RIGHT_A), rightEncoderISR, CHANGE);
    attachInterrupt(digitalPinToInterrupt(ENCODER_RIGHT_B), rightEncoderISR, CHANGE);

    Wire.begin();
    Wire.setClock(400000); // Set I2C to 400kHz (Fast Mode)
    Serial.begin(BAUD_RATE);
    Serial.setTimeout(50);

    lcd.init();
    lcd.backlight();
    lcd.setCursor(0, 0);
    updateLCD();
    delay(1000); // Allow time for sensors to stabilize
    digitalWrite(STBY, HIGH);
    
    
    if (initMPU6050())
    {
        strncpy(lcdLine1, "MPU OK", sizeof(lcdLine1));
        lcdLine1[16] = '\0';
        triggerUltrasonicPulse();
        getMPUData(ax, ay, az, gx, gy, gz, tempC);
    }
    else
    {
        strncpy(lcdLine1, "MPU Error", sizeof(lcdLine1));
        lcdLine1[16] = '\0';
    }
    
    lastPIDComputeTime = micros();
}

uint8_t expectedCommandLength(uint8_t cmd)
{
    if (cmd == CMD_MOVE)
        return 7;
    if (cmd == CMD_LCD_UPDATE)
        return 35;
    if (cmd == CMD_STOP)
        return 3;
    if (cmd == CMD_ENABLE)
        return 3;
    return 0; // invalid
}

void handleIncomingData() {
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
            handleCommand(cmdBuf, expected);
            cmdIdx = 0;
        }
    }
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

void triggerUltrasonicPulse()
{
    digitalWrite(TRIGGER, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIGGER, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIGGER, LOW);
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

    ax = (Wire.read() << 8) | Wire.read();
    ay = (Wire.read() << 8) | Wire.read();
    az = (Wire.read() << 8) | Wire.read();

    int16_t tempRaw = (Wire.read() << 8) | Wire.read();
    tempC = tempRaw / 340.0 + 36.53;

    gx = (Wire.read() << 8) | Wire.read();
    gy = (Wire.read() << 8) | Wire.read();
    gz = (Wire.read() << 8) | Wire.read();
}


float getLeftMotorSpeed(int32_t left, int32_t lastLeft)
{
    deltaLeftTicks = left - lastLeft;
    deltaLeft = (deltaLeftTicks * (PI * WHEEL_DIAMETER) / ENCODER_TICKS_PER_REV);
    return deltaLeft / (PID_INTERVAL / 1000.0); // Convert to m/s
}

float getRightMotorSpeed(int32_t right, int32_t lastRight)
{
    deltaRightTicks = right - lastRight;
    deltaRight = (deltaRightTicks * (PI * WHEEL_DIAMETER) / ENCODER_TICKS_PER_REV);
    return deltaRight / (PID_INTERVAL / 1000.0); // Convert to m/s
}

int applyDeadband(float pwm) {
    int sign = (pwm >= 0) ? 1 : -1;
    float mag = abs(pwm);

    if (mag == 0) return 0;
    
    if (mag > MAX_PWM) mag = MAX_PWM; // Cap the magnitude to max PWM
    
    // Scale 0–255 PID output into 50–255 motor range
    float scaled = MIN_PWM + (mag / MAX_PWM) * (MAX_PWM - MIN_PWM);

    return sign * (int)scaled;
}

void pidLoop(int32_t left, int32_t lastLeft, int32_t right, int32_t lastRight){
    float leftSpeed = getLeftMotorSpeed(left, lastLeft);
    float rightSpeed = getRightMotorSpeed(right, lastRight);
    
    float leftOutput = pidLeft.compute(leftSpeed);
    float rightOutput = pidRight.compute(rightSpeed);
    
    handleMovement(applyDeadband(leftOutput), applyDeadband(rightOutput));
}

void echoISR() {
    if (digitalRead(ECHO) == HIGH) {
        echoStart = micros();
    } else {
        echoDuration = micros() - echoStart;
        if (echoDuration > 25000) {
            echoDuration = -1; // Timeout, no echo received
        } else if (echoDuration < 100) {
            echoDuration = -2; // Too close, likely noise
        }
        
        echoReady = true;
    }
}

uint8_t getBatteryPercent()
{
    int raw = analogRead(BATTERY);  // 0–1023
    float voltageAtPin = raw * (5.0 / 1023.0);
    float batteryVoltage = voltageAtPin * 13.0 / 3.0; // because of 10k & 3k
    float maxV = 8.4; // 2S LiPo max voltage
    float minV = 6.0; // 2S LiPo min voltage
    
    float percent = (batteryVoltage - minV) / (maxV - minV) * 100.0;
    return constrain((uint8_t)percent, 0, 100);
}

void sendSensorData(int32_t leftEncoder, int32_t rightEncoder)
{
    // Get ultrasonic data
    float distance = lastDistance;

    uint8_t ir_front = getIRFront();
    uint8_t ir_back = getIRBack();
    uint8_t flags = (ir_front << 0) | (ir_back << 1); // bit 0 = front, bit 1 = back
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
    packet.start = 0xAA;
    packet.packetSeq = packetSeq++;
    packet.distance = distance;
    packet.ax = ax;
    packet.ay = ay;
    packet.az = az;
    packet.gx = gx;
    packet.gy = gy;
    packet.gz = gz;
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
        // Checksum error
        strncpy(lcdLine1, "Checksum Err", sizeof(lcdLine1));
        lcdLine1[16] = '\0';
       
        strncpy(lcdLine2, "Invalid Data", sizeof(lcdLine2));
        lcdLine2[16] = '\0';
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
        
        char lcd_buffer[17];
        sprintf(lcd_buffer, "L:%d R:%d", leftVel, rightVel);

        strncpy(lcdLine1, lcd_buffer, sizeof(lcdLine1));
        lcdLine1[16] = '\0';
        
        strncpy(lcdLine2, "Moving", sizeof(lcdLine2));
        lcdLine2[16] = '\0';
    }
    else if (cmd == CMD_LCD_UPDATE && length == 35)
    {
        // Command 0x02: Update LCD with two lines of text
        memcpy(lcdLine1, &buffer[2], 16);
        lcdLine1[16] = '\0';
        memcpy(lcdLine2, &buffer[18], 16);
        lcdLine2[16] = '\0';
        
    } else if (cmd == CMD_ENABLE && length == 3){
        // Command 0x03: ENABLE
        motorsEnabled = true;
        digitalWrite(STBY, HIGH);
        
        strncpy(lcdLine1, "ENABLE CMD", sizeof(lcdLine1));
        lcdLine1[16] = '\0';
        strncpy(lcdLine2, "Motors enabled", sizeof(lcdLine2));
        lcdLine2[16] = '\0';
    } else if (cmd == CMD_STOP && length == 3){
      // Command 0x04: STOP
        motorsEnabled = false;
        motorsRunning = false;
        
        pidLeft.reset();
        pidRight.reset();
        
        digitalWrite(STBY, LOW);
        
        strncpy(lcdLine1, "STOP COMMAND", sizeof(lcdLine1));
        lcdLine1[16] = '\0';
        strncpy(lcdLine2, "Motors stopped", sizeof(lcdLine2));
        lcdLine2[16] = '\0';
    }
    else
    {
        strncpy(lcdLine1, "Invalid Cmd", sizeof(lcdLine1));
        lcdLine1[16] = '\0';
        strncpy(lcdLine2, "Check Serial", sizeof(lcdLine2));
        lcdLine2[16] = '\0';
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
        analogWrite(EN1, leftSpeed);
    }
    else if (leftSpeed < 0)
    {
        digitalWrite(IN1, LOW);
        digitalWrite(IN2, HIGH);
        analogWrite(EN1, -leftSpeed);
    }
    else
    {
        digitalWrite(IN1, LOW);
        digitalWrite(IN2, LOW);
        analogWrite(EN1, 0);
    }

    if (rightSpeed > 0)
    {
        digitalWrite(IN3, HIGH);
        digitalWrite(IN4, LOW);
        analogWrite(EN2, rightSpeed);
    }
    else if (rightSpeed < 0)
    {
        digitalWrite(IN3, LOW);
        digitalWrite(IN4, HIGH);
        analogWrite(EN2, -rightSpeed);
    }
    else
    {
        digitalWrite(IN3, LOW);
        digitalWrite(IN4, LOW);
        analogWrite(EN2, 0);
    }
    
    if (leftSpeed != 0 || rightSpeed != 0){
        motorsRunning = true;
    } else {
        motorsRunning = false;
    }
}

void updateLCD()
{
    strncpy(lastLine1, lcdLine1, sizeof(lastLine1));
    strncpy(lastLine2, lcdLine2, sizeof(lastLine2));
    
    // Pad with spaces to clear old content
    for (int i = strlen(lastLine1); i < 16; i++) {
        lastLine1[i] = ' ';
    }
    
    for (int i = strlen(lastLine2); i < 16; i++) {
        lastLine2[i] = ' ';
    }
    
    lcd.setCursor(0, 0);
    lcd.print(lcdLine1);
    lcd.setCursor(0, 1);
    lcd.print(lcdLine2);
}

void loop()
{
    unsigned long now = micros();
    const unsigned long PID_INTERVAL_US = (unsigned long)PID_INTERVAL * 1000UL;
    
    
    // High priority: Run PID loop and send sensor data at 100 Hz
    
    if (now - lastPIDComputeTime >= PID_INTERVAL_US)
    {
        lastPIDComputeTime += PID_INTERVAL_US;
        int32_t currentLeftEncoder;
        int32_t currentRightEncoder;
        int32_t lastLeftEncoder;
        int32_t lastRightEncoder;
        
        noInterrupts();
        currentLeftEncoder = leftEncoderCount;
        currentRightEncoder = rightEncoderCount;
        lastLeftEncoder = lastLeftEncoderCount;
        lastRightEncoder = lastRightEncoderCount;
        interrupts();
        
        getMPUData(ax, ay, az, gx, gy, gz, tempC);
        pidLoop(currentLeftEncoder, lastLeftEncoder, currentRightEncoder, lastRightEncoder);
        sendSensorData(currentLeftEncoder, currentRightEncoder);
    }
    
    handleIncomingData();

    // Medium priority: Sample ultrasonic sensor at 20 Hz
    
    if (millis() - lastUltrasonicSampleTime >= ULTRASONIC_INTERVAL){
      triggerUltrasonicPulse();
      lastUltrasonicSampleTime = millis();
    }
    
    if (echoReady) {
        echoReady = false;
        if (echoDuration == 0 || echoDuration > 25000) {
            lastDistance = -1;
        } else if (echoDuration < 100) {
            lastDistance = -2;
        } else {
            lastDistance = (echoDuration / 2.0) * 0.0343;
        }
    }
    
    // Low priority: Update LCD at 2 Hz, but only if content has changed

    if (millis() - lastLCDUpdateTime >= LCD_UPDATE_INTERVAL){
        // Update LCD only if the content has changed'
       if (strncmp(lcdLine1, lastLine1, sizeof(lcdLine1)) != 0 || strncmp(lcdLine2, lastLine2, sizeof(lcdLine2)) != 0) {
            updateLCD();
        }
       lastLCDUpdateTime = millis();  
    }
}
