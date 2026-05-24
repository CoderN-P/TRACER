#include "sensors.h"
#include "config.h"
#include "globals.h"
#include <Arduino.h>
#include <Wire.h>
#include "soc/gpio_struct.h"
#include <VL53L0X.h>

volatile uint32_t echoStart1 = 0;
volatile int32_t echoDuration1 = 0;
volatile uint32_t echoStart2 = 0;
volatile int32_t echoDuration2 = 0;

VL53L0X sensor;

static inline bool takeI2CMutex(TickType_t timeoutTicks = pdMS_TO_TICKS(5))
{
    return (i2c_mutex != NULL) && (xSemaphoreTake(i2c_mutex, timeoutTicks) == pdTRUE);
}

bool setup_lsm6dos()
{
    if (!takeI2CMutex())
    {
        return false;
    }

    
    // PIN_CTRL: Pin control register
    // 01111111 = 0x7F
    // (SDO Pullups enabled)
    Wire.beginTransmission(LSM_ADDRESS);
    Wire.write(LSM_PIN_CTRL);
    Wire.write(0x7F);
    Wire.endTransmission();
    
    // CTRL2_G: Gyroscope control register
    // 01000000 = 0x40 
    // (ODR: 104 Hz | Range: +- 250 dps)
    Wire.beginTransmission(LSM_ADDRESS);
    Wire.write(LSM_GYRO_CTRL);
    Wire.write(0x40);      
    Wire.endTransmission(); 
    
    // CTRL1_XL: Accelerometer control register
    // 01000010 = 0x42
    // (ODR: 104 Hz | Range: +- 2g | 2 stage filtering enabled)
    Wire.beginTransmission(LSM_ADDRESS);
    Wire.write(LSM_ACCEL_CTRL);
    Wire.write(0x42);
    Wire.endTransmission();
    
    // CTRL8_XL: Secondary accelerometer control register
    // 01101000 = 0x68
    // (LP Filter Bandwidth: ODR/45 | Fast settling ode enabled | LP filter enabled)
    Wire.beginTransmission(LSM_ADDRESS);
    Wire.write(LSM_CTRL8_XL);
    Wire.write(0x68);
    Wire.endTransmission();
    
    // CTRL7_G: Secondary gyroscope control register
    // 10000000 = 0x80
    // (High performance mode enabled | High pass filter disabled )
    Wire.beginTransmission(LSM_ADDRESS);
    Wire.write(LSM_CTRL7_G);
    Wire.write(0x80);
    Wire.endTransmission();
    
    // CTRL3_C: Operating settings register
    // 01000100 = 0x44
    // (Block data update enabled | Auto increment address enabled)
    Wire.beginTransmission(LSM_ADDRESS);
    Wire.write(LSM_CTRL3_C);
    Wire.write(0x44); 
    Wire.endTransmission();
    
    byte status = Wire.endTransmission(true);
    xSemaphoreGive(i2c_mutex);
    return status == 0; // Return true if successful
}

void setup_magnetometer()
{
    if (!takeI2CMutex())
    {
        return;
    }

    Wire.beginTransmission(MAG_ADDRESS);
    // Control Register 1 (0x09)
    // 0x05 = 0b00000101
    // (OSR: 512 | Range: 2G | ODR: 50Hz* | Mode: Continuous)
    Wire.write(0x09);
    Wire.write(0x05);
    Wire.endTransmission();

    // CRITICAL: Set/Reset Period Register (0x0B)
    // The sensor will NOT update correctly without this!
    Wire.beginTransmission(MAG_ADDRESS);
    Wire.write(0x0B);
    Wire.write(0x01); // Standard recommended value
    Wire.endTransmission();
    xSemaphoreGive(i2c_mutex);
}

uint8_t getBatteryPercent()
{
    int raw = analogRead(BATTERY); // 0–4095
    float voltageAtPin = raw * (3.3 / 4095.0);
    float batteryVoltage = voltageAtPin * 13.0 / 3.0; // because of 10k & 3k
    float maxV = 12.6;                                // 3S LiPo max voltage
    float minV = 9.0;                                 // 3S LiPo min voltage

    float percent = (batteryVoltage - minV) / (maxV - minV) * 100.0;
    return constrain((uint8_t)percent, 0, 100);
}

void getLSMData(int16_t &ax, int16_t &ay, int16_t &az, int16_t &gx, int16_t &gy, int16_t &gz, int16_t &tempC)
{
    if (!takeI2CMutex(pdMS_TO_TICKS(3.5)))
    {
        return;
    }

    Wire.beginTransmission(LSM_ADDRESS);
    Wire.write(LSM_DATA_REG); // Starting register for accelerometer + temp + gyro data
    Wire.endTransmission(false);
    Wire.requestFrom(LSM_ADDRESS, 14); // Request 14 bytes (6 for accelerometer, 6 for gyroscope, 2 for temperature)

    if (Wire.available() < 14)
    {
        xSemaphoreGive(i2c_mutex);
        return;
    }

    // Little endian - LSB comes first
    // Raw values adjusted on raspberry pi side to minimize sensor packet size
    
    tempC = (int16_t) ((Wire.read()) | (Wire.read() << 8));
    
    gx = (int16_t) (((Wire.read()) | (Wire.read() << 8))); 
    gy = (int16_t) (((Wire.read()) | (Wire.read() << 8))); 
    gz = (int16_t) (((Wire.read()) | (Wire.read() << 8))); 
    
    ax = (int16_t) (((Wire.read()) | (Wire.read() << 8))); 
    ay = (int16_t) (((Wire.read()) | (Wire.read() << 8))); 
    az = (int16_t) (((Wire.read()) | (Wire.read() << 8))); 

    xSemaphoreGive(i2c_mutex);
}

void getMagnetometerData(int16_t &magX, int16_t &magY, int16_t &magZ)
{
    if (!takeI2CMutex(pdMS_TO_TICKS(3.5)))
    {
        return;
    }

    Wire.beginTransmission(MAG_ADDRESS);
    Wire.write(MAG_DATA_REG); // Starting register for magnetometer data
    Wire.endTransmission(false);
    Wire.requestFrom(MAG_ADDRESS, 6); // Request 6 bytes (2 for each axis)

    if (Wire.available() < 6)
    {
        xSemaphoreGive(i2c_mutex);
        return;
    }

    // Little Endian - LSB comes first
    magX = (int16_t) (Wire.read() | (Wire.read() << 8)); 
    magY = (int16_t) (Wire.read() | (Wire.read() << 8));
    magZ = (int16_t) (Wire.read() | (Wire.read() << 8));

    xSemaphoreGive(i2c_mutex);
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

void IRAM_ATTR echoISR1()
{
    bool echoState = (GPIO.in >> ECHO_1) & 1;
    uint32_t now = xthal_get_ccount() / 240; // CPU cycles / MHz = microseconds
    if (echoState)
    {
        echoStart1 = now;
    }
    else
    {
        uint32_t duration = now - echoStart1;
        echoDuration1 = (int32_t)duration;
    }
}

void IRAM_ATTR echoISR2()
{
    bool echoState = (GPIO.in >> ECHO_2) & 1;
    uint32_t now = xthal_get_ccount() / 240; // CPU cycles / MHz = microseconds
    if (echoState)
    {
        echoStart2 = now;
    }
    else
    {
        uint32_t duration = now - echoStart2;
        echoDuration2 = (int32_t)duration;
    }
}

bool setup_tof()
{
    if (!takeI2CMutex(pdMS_TO_TICKS(20)))
    {
        return false;
    }

    sensor.setTimeout(50);
    
    if (!sensor.init())
    {
        xSemaphoreGive(i2c_mutex);
        return false;
    }
    
    sensor.setMeasurementTimingBudget(50000);
    sensor.startContinuous();
    xSemaphoreGive(i2c_mutex);
    return true;
}

void getToFDistance(int16_t &distanceFront)
{

    if (!takeI2CMutex(pdMS_TO_TICKS(10)))
    {
        return;
    }
    
    uint16_t dist = sensor.readRangeContinuousMillimeters();
    
    if (sensor.timeoutOccurred()) 
    {
        xSemaphoreGive(i2c_mutex); // Bus is free for other tasks instantly (~0.5ms lock time)
        return; // Exit and wait for the next 10Hz loop tick
    }
        
    xSemaphoreGive(i2c_mutex);
    
    if (dist < 1200)
    {                                                    
        distanceFront = dist; // Keep in mm
    }
    else
    {
        distanceFront = -1; // Indicate out of range
    }
}