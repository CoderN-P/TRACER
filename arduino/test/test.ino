#include <SoftwareSerial.h>
#include <ArduinoJson.h>
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
const int TRIGGER = 2; // Trigger pin for ultrasonic sensor
const int ECHO = 11;   // Echo pin for ultrasonic sensor
const int MAX_BUFFER_SIZE = 512;
const int MPUAddress = 0x68; // I2C address for MPU6050

unsigned long lastSensorSendTime = 0;
const unsigned long sensorInterval = 100;

String jsonBuffer = "";

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

    Wire.begin();
    Serial.begin(115200);
    

    lcd.init();
    lcd.backlight();
    lcd.setCursor(0, 0);
    if (initMPU6050())
    {
        lcd.println("MPU OK");
    }
    else
    {
        lcd.print("MPU ERROR");
    }
}

void handleIncomingData()
{
    if (Serial.available() > 0)
    {
        jsonBuffer = Serial.readStringUntil('\n'); // Read until newline
        processJsonMessage();
    }
}

bool getIRFront()
{
    return digitalRead(IR_FRONT) == HIGH;
}

bool getIRBack()
{
    return digitalRead(IR_BACK) == HIGH;
}

StaticJsonDocument<200> getUltrasonicData()
{
    // Trigger the ultrasonic sensor
    digitalWrite(TRIGGER, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIGGER, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIGGER, LOW);

    // Read the echo time with timeout
    long duration = pulseIn(ECHO, HIGH, 30000); // 30ms timeout

    // Calculate distance in cm
    float distance = (duration == 0) ? -1 : (duration / 2.0) * 0.0343; // -1 indicates timeout
    StaticJsonDocument<200> doc;
    doc["distance"] = distance;
    return doc;
}

StaticJsonDocument<200> getMPUData()
{
    Wire.beginTransmission(MPUAddress);
    Wire.write(0x3B); // Starting register for accelerometer data
    Wire.endTransmission(false);
    Wire.requestFrom(MPUAddress, 14); // Request 14 bytes (6 for accelerometer, 6 for gyroscope, 2 for temperature)

    StaticJsonDocument<200> doc;

    if (Wire.available() < 14)
    {
        doc["error"] = "Incomplete data";
        return doc;
    }

    int16_t ax = (Wire.read() << 8) | Wire.read();
    int16_t ay = (Wire.read() << 8) | Wire.read();
    int16_t az = (Wire.read() << 8) | Wire.read();

    int16_t tempRaw = (Wire.read() << 8) | Wire.read();
    float tempC = tempRaw / 340.0 + 36.53;

    int16_t gx = (Wire.read() << 8) | Wire.read();
    int16_t gy = (Wire.read() << 8) | Wire.read();
    int16_t gz = (Wire.read() << 8) | Wire.read();

    doc["acceleration_x"] = ax;
    doc["acceleration_y"] = ay;
    doc["acceleration_z"] = az;

    doc["temperature"] = tempC;

    doc["gyroscope_x"] = gx;
    doc["gyroscope_y"] = gy;
    doc["gyroscope_z"] = gz;

    return doc;
}

StaticJsonDocument<512> getSensorData()
{
    StaticJsonDocument<512> doc;

    // Get ultrasonic data
    StaticJsonDocument<200> ultrasonicData = getUltrasonicData();
    doc["ultrasonic"] = ultrasonicData;

    // Get MPU data
    StaticJsonDocument<200> mpuData = getMPUData();
    doc["imu"] = mpuData;

    doc["ir_front"] = getIRFront();
    doc["ir_back"] = getIRBack();

    return doc;
}

void processJsonMessage()
{
    if (jsonBuffer.length() == 0)
        return;

    // Remove any trailing whitespace/newlines
    jsonBuffer.trim();

    // Parse JSON
    StaticJsonDocument<512> doc;
    DeserializationError error = deserializeJson(doc, jsonBuffer);

    if (error)
    {
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.println("JSON Error");
        return;
    }

    // Process the command
    String commandType = doc["command_type"];
    JsonObject command = doc["command"];

    if (commandType == "MOTOR")
    {
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.println("Motor Command");
        float leftSpeed = command["left_motor"];
        float rightSpeed = command["right_motor"];
        handleMovement(leftSpeed, rightSpeed);
    }
}

void handleMovement(float leftSpeed, float rightSpeed)
{
    // Values already mapped between -255 and 255

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

void sendSensorData()
{
    // Example sensor data
    StaticJsonDocument<512> doc = getSensorData();
    String output;
    serializeJson(doc, output);
    Serial.println(output);
}

void loop()
{
    handleIncomingData();
    if (millis() - lastSensorSendTime >= sensorInterval)
    {
        sendSensorData();
        lastSensorSendTime = millis();
    }
}