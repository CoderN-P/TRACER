#include <SoftwareSerial.h>
#include <ArduinoJson.h>
#include <LiquidCrystal_I2C.h>
#include  <Wire.h>

const int EN1 = 9; // Enable pin for motor 1
const int IN1 = 3; // Input pin 1 for motor 1
const int IN2 = 4; // Input pin 2 for motor 1
const int EN2 = 5; // Enable pin for motor 2
const int IN3 = 6; // Input pin 1 for motor 2
const int IN4 = 7; // Input pin 2 for motor 2
const int TRIGGER = 2; // Trigger pin for ultrasonic sensor
const int ECHO = 10; // Echo pin for ultrasonic sensor
const int MAX_BUFFER_SIZE = 512;
const int MPUAddress = 0x68; // I2C address for MPU6050


unsigned long lastSensorSendTime = 0;
const unsigned long sensorInterval = 100;

String jsonBuffer = "";

LiquidCrystal_I2C lcd(0x27,  16, 2);

void setup() {
    pinMode(EN1, OUTPUT);
    pinMode(IN1, OUTPUT);
    pinMode(IN2, OUTPUT);
    pinMode(EN2, OUTPUT);
    pinMode(IN3, OUTPUT);
    pinMode(IN4, OUTPUT);
    pinMode(TRIGGER, OUTPUT);
    pinMode(ECHO, INPUT);
    
    Serial.begin(9600);
  
    lcd.init();
    lcd.backlight();
}

void handleIncomingData() {
    // Check if Bluetooth is connected
  
    
  while (Serial.available()) {
    char incomingChar = Serial.read();
    
    // Add character to buffer
    jsonBuffer += incomingChar;
    Serial.println("received");
    
    // Check for complete message (assuming newline delimiter)
    if (incomingChar == '\n' || incomingChar == '\r') {
      lcd.print("Received !");
      processJsonMessage();
      jsonBuffer = ""; // Clear buffer
    }
    
    // Prevent buffer overflow
    if (jsonBuffer.length() > MAX_BUFFER_SIZE) {
      jsonBuffer = "";
    }
  }
}

StaticJsonDocument<200> getUltrasonicData() {
    // Trigger the ultrasonic sensor
    digitalWrite(TRIGGER, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIGGER, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIGGER, LOW);
    
    // Read the echo time
    long duration = pulseIn(ECHO, HIGH);
    
    // Calculate distance in cm
    float distance = (duration / 2.0) * 0.0343;
    StaticJsonDocument<200> doc;
    doc["distance"] = distance;
    return doc;
}

StaticJsonDocument<200> getMPUData() {
    Wire.beginTransmission(MPUAddress);
    Wire.write(0x3B); // Starting register for accelerometer data
    Wire.endTransmission(false);
    Wire.requestFrom(MPUAddress, 14); // Request 14 bytes (6 for accelerometer, 6 for gyroscope, 2 for temperature)
    
    if (Wire.available() < 14) {
        return StaticJsonDocument<200>(); // Return empty document if not enough data
    }
    
    int16_t ax = (Wire.read() << 8) | Wire.read();
    int16_t ay = (Wire.read() << 8) | Wire.read();
    int16_t az = (Wire.read() << 8) | Wire.read();
    
    StaticJsonDocument<200> doc;
    doc["acceleration_x"] = ax;
    doc["acceleration_y"] = ay;
    doc["acceleration_z"] = az;
    
    doc["temperature"] = (Wire.read() << 8) | Wire.read(); // Read temperature data
    
    doc["gyroscope_x"] = (Wire.read() << 8) | Wire.read();
    doc["gyroscope_y"] = (Wire.read() << 8) | Wire.read();
    doc["gyroscope_z"] = (Wire.read() << 8) | Wire.read();
    
    
    return doc;
}

StaticJsonDocument<512> getSensorData() {
    StaticJsonDocument<512> doc;
    
    // Get ultrasonic data
    StaticJsonDocument<200> ultrasonicData = getUltrasonicData();
    doc["ultrasonic"] = ultrasonicData;
    
    // Get MPU data
    StaticJsonDocument<200> mpuData = getMPUData();
    doc["imu"] = mpuData;
    
    return doc;
}

void processJsonMessage() {
  if (jsonBuffer.length() == 0) return;
  
  // Remove any trailing whitespace/newlines
  jsonBuffer.trim();
  
  // Parse JSON
  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, jsonBuffer);
  
  if (error) {
    lcd.println("JSON Error!");
    return;
  }
  
  // Process the command
  String commandType = doc["command_type"];
  JsonObject command = doc["command"];
  
  if (commandType == "MOTOR") {
    lcd.println("Motor Command");
    float leftSpeed = command["left_motor"];
    float rightSpeed = command["right_motor"];
    handleMovement(leftSpeed, rightSpeed);
  }
}


void handleMovement(float leftSpeed, float rightSpeed){
     // Values already mapped between -255 and 255
     
    if (leftSpeed > 0) {
        digitalWrite(IN1, HIGH);
        digitalWrite(IN2, LOW);
        analogWrite(EN1, leftSpeed);
    } else if (leftSpeed < 0) {
        digitalWrite(IN1, LOW);
        digitalWrite(IN2, HIGH);
        analogWrite(EN1, -leftSpeed);
    } else {
        digitalWrite(IN1, LOW);
        digitalWrite(IN2, LOW);
        analogWrite(EN1, 0);
    }
    
    if (rightSpeed > 0) {
        digitalWrite(IN3, HIGH);
        digitalWrite(IN4, LOW);
        analogWrite(EN2, rightSpeed);
    } else if (rightSpeed < 0) {
        digitalWrite(IN3, LOW);
        digitalWrite(IN4, HIGH);
        analogWrite(EN2, -rightSpeed);
    } else {
        digitalWrite(IN3, LOW);
        digitalWrite(IN4, LOW);
        analogWrite(EN2, 0);
    }
}

void sendSensorData() {
    // Example sensor data
    StaticJsonDocument<200> doc = getSensorData();
    String output;
    serializeJson(doc, output);
    Serial.println(output);
}

void loop(){
   handleIncomingData();
   if (millis() - lastSensorSendTime >= sensorInterval) {
       sendSensorData();
       lastSensorSendTime = millis();
   }
}