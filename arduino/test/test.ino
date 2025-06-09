#include <LiquidCrystal_I2C.h>
#include <Wire.h>

const int EN1 = 9; // Enable pin for motor 1
const int IN1 = 3; // Input pin 1 for motor 1
const int IN2 = 4; // Input pin 2 for motor 1
const int EN2 = 5; // Enable pin for motor 2
const int IN3 = 6; // Input pin 1 for motor 2
const int IN4 = 7; // Input pin 2 for motor 2
const int IR_FRONT = 8;
const int IR_BACK = 12;
const int STBY = 13;
const int TRIGGER = 2; // Trigger pin for ultrasonic sensor
const int ECHO = 11;   // Echo pin for ultrasonic sensor
const int MAX_BUFFER_SIZE = 512;
const int MPUAddress = 0x68; // I2C address for MPU6050
unsigned long lastUltrasonicSampleTime = 0;
unsigned long lastMPUSampleTime = 0;
unsigned long lastLCDUpdateTime = 0;
bool bufferSensorSending = false;
bool motorsEnabled = true;
int ax, ay, az, gx, gy, gz;
float lastDistance, tempC;
char lastLine1[17] = "";
char lastLine2[17] = "";
char lcdLine1[17] = "Init...";
char lcdLine2[17] = "";

LiquidCrystal_I2C lcd(0x27, 16, 2);

bool initMPU6050()
{
    Wire.beginTransmission(MPUAddress);
    Wire.write(0x6B); // PWR_MGMT_1 register
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

    Wire.begin();
    Serial.begin(115200);
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
        getUltrasonicData(lastDistance);
        getMPUData(ax, ay, az, gx, gy, gz, tempC);
    }
    else
    {
        strncpy(lcdLine1, "MPU Error", sizeof(lcdLine1));
        lcdLine1[16] = '\0';
    }
}

uint8_t expected_command_length(uint8_t cmd)
{
    if (cmd == 0x01)
        return 6;
    if (cmd == 0x02)
        return 34;
    if (cmd == 0x03)
        return 2;
    if (cmd == 0x04)
        return 2;
    return 255; // invalid
}

void handleIncomingData()
{
    if (Serial.available() > 0)
    {
        static byte buf[64];
        static size_t idx = 0;

        while (Serial.available())
        {
            buf[idx++] = Serial.read();
            if (idx == expected_command_length(buf[0]))
            {
                handleCommand(buf, idx);
                idx = 0;
            }
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


void getUltrasonicData(float &distance)
{
    digitalWrite(TRIGGER, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIGGER, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIGGER, LOW);

    // Use a shorter timeout to prevent blocking
    long duration = pulseIn(ECHO, HIGH, 25000); // 25ms timeout (~4.25m max)
    
    if (duration == 0)
    {
        distance = -1; // Indicate too far
        return;
    } else if (duration < 100) 
    {
        distance = -2; // Indicate too close
        return;
    }
    distance = (duration / 2.0) * 0.0343; // Convert to cm
}

void getMPUData(int &ax, int &ay, int &az, int &gx, int &gy, int &gz, float &tempC)
{
    Wire.beginTransmission(MPUAddress);
    Wire.write(0x3B); // Starting register for accelerometer data
    Wire.endTransmission(false);
    Wire.requestFrom(MPUAddress, 14); // Request 14 bytes (6 for accelerometer, 6 for gyroscope, 2 for temperature)

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

void sendSensorData()
{

    // Get ultrasonic data
    float distance = lastDistance;

    uint8_t ir_front = getIRFront();
    uint8_t ir_back = getIRBack();
    uint8_t ir_flags = (ir_front << 0) | (ir_back << 1); // bit 0 = front, bit 1 = back

    byte buffer[20];
    int i = 0;

    buffer[i++] = 0xAA; // Start byte
    memcpy(&buffer[i], &distance, 4); // Store distance as float
    i += 4; // Store distance as float
    memcpy(&buffer[i], &ax, 2);
    i += 2;
    memcpy(&buffer[i], &ay, 2);
    i += 2;
    memcpy(&buffer[i], &az, 2);
    i += 2;
    memcpy(&buffer[i], &gx, 2);
    i += 2;
    memcpy(&buffer[i], &gy, 2);
    i += 2;
    memcpy(&buffer[i], &gz, 2);
    i += 2;
    memcpy(&buffer[i], &tempC, 4);
    i += 4;                 // Store temperature as float
    buffer[i++] = ir_flags; // Store IR flags

    uint8_t checksum = 0;
    for (int j = 1; j < i; j++)
        checksum += buffer[j];
    buffer[i++] = checksum;

    Serial.write(buffer, i); // Send the data over Serial
    
    if (bufferSensorSending){
        bufferSensorSending = false;
    }
}


void handleCommand(byte *buffer, size_t length)
{
    uint8_t cmd = buffer[0];

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

    if (cmd == 0x01 && length == 6)
    {
        // Command 0x01: Handle movement
        int16_t left, right;
        memcpy(&left, &buffer[1], 2);
        memcpy(&right, &buffer[3], 2);
        
        handleMovement(left, right);

        char lcd_buffer[17];
        sprintf(lcd_buffer, "L:%d R:%d", left, right);

        strncpy(lcdLine1, lcd_buffer, sizeof(lcdLine1));
        lcdLine1[16] = '\0';
        
        strncpy(lcdLine2, "Moving", sizeof(lcdLine2));
        lcdLine2[16] = '\0';
        
        bufferSensorSending = true; // Set flag to send sensor data next loop
    }
    else if (cmd == 0x02 && length == 34)
    {
        // Command 0x02: Update LCD with two lines of text
        bufferSensorSending = true; // Set flag to send sensor data next loop
        memcpy(lcdLine1, &buffer[1], 16);
        memcpy(lcdLine2, &buffer[17], 16);
        
    }
    else if (cmd == 0x03 && length == 2)
    {
        // Command 0x03: Request sensor data
        bufferSensorSending = true; // Set flag to send sensor data next loop
    } else if (cmd == 0x04 && length == 2){
      // Command 0x04: STOP
        motorsEnabled = false;
        digitalWrite(STBY, LOW);
        bufferSensorSending = true; // Stop sending sensor data
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

void handleMovement(int16_t leftSpeed, int16_t rightSpeed)
{
    // Values already mapped between -255 and 255

    if (!motorsEnabled){
      digitalWrite(STBY, HIGH);
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
}

void loop()
{

    handleIncomingData();

    if (millis() - lastUltrasonicSampleTime >= 30){
      getUltrasonicData(lastDistance);
      lastUltrasonicSampleTime = millis();
    }

    if (millis() - lastMPUSampleTime >= 10){
      getMPUData(ax, ay, az, gx, gy, gz, tempC);
      lastMPUSampleTime = millis();
    }

    if (millis() - lastLCDUpdateTime >= 500){
        // Update LCD only if the content has changed'
       if (strncmp(lcdLine1, lastLine1, sizeof(lcdLine1)) != 0 || strncmp(lcdLine2, lastLine2, sizeof(lcdLine2)) != 0) {
            updateLCD();
        }
       lastLCDUpdateTime = millis();  
    }
    
    if (bufferSensorSending)
    {
        sendSensorData();
    }
}

void updateLCD()
{
    strncpy(lastLine1, lcdLine1, sizeof(lastLine1));
    strncpy(lastLine2, lcdLine2, sizeof(lastLine2));
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print(lcdLine1);
    lcd.setCursor(0, 1);
    lcd.print(lcdLine2);
}