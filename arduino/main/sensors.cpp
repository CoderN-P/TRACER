#include "sensors.h"
#include "config.h"
#include "globals.h"
#include <Arduino.h>
#include <Wire.h>
#include "soc/gpio_struct.h"
#include "Adafruit_VL53L0X.h"

volatile uint32_t echoStart1 = 0;
volatile int32_t echoDuration1 = 0;
volatile uint32_t echoStart2 = 0;
volatile int32_t echoDuration2 = 0;

Adafruit_VL53L0X lox = Adafruit_VL53L0X();

static inline bool takeI2CMutex(TickType_t timeoutTicks = pdMS_TO_TICKS(5))
{
    return (i2c_mutex != NULL) && (xSemaphoreTake(i2c_mutex, timeoutTicks) == pdTRUE);
}

bool initMPU6050()
{
    if (!takeI2CMutex())
    {
        return false;
    }

    Wire.beginTransmission(MPU_ADDRESS);
    Wire.write(PWR_MGMT_1); // PWR_MGMT_1 register
    Wire.write(0);          // Wake up the MPU-6050 (0 = wake up)
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

    /*
      uint8_t MODE_CONTINUOUS = 0b00000001;
      uint8_t ODR_50Hz = 0b00000100;
      uint8_t LSB_2G = 0b00000000;
      uint8_t OSR_512 = 0x00;
      Wire.beginTransmission(MAG_ADDRESS);
      Wire.write(MAG_CTRL_REG);
      Wire.write(MODE_CONTINUOUS | ODR_50Hz | LSB_2G | OSR_512);
      Wire.endTransmission();
    */

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

void getMPUData(int &ax, int &ay, int &az, int &gx, int &gy, int &gz, float &tempC)
{
    if (!takeI2CMutex())
    {
        return;
    }

    Wire.beginTransmission(MPU_ADDRESS);
    Wire.write(0x3B); // Starting register for accelerometer data
    Wire.endTransmission(false);
    Wire.requestFrom(MPU_ADDRESS, 14); // Request 14 bytes (6 for accelerometer, 6 for gyroscope, 2 for temperature)

    if (Wire.available() < 14)
    {
        xSemaphoreGive(i2c_mutex);
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

    xSemaphoreGive(i2c_mutex);
}

void getMagnetometerData(float &magX, float &magY, float &magZ)
{
    if (!takeI2CMutex())
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

    uint16_t x_u = (uint16_t)(Wire.read() | (Wire.read() << 8)); // LSB comes first
    uint16_t y_u = (uint16_t)(Wire.read() | (Wire.read() << 8));
    uint16_t z_u = (uint16_t)(Wire.read() | (Wire.read() << 8));

    magX = ((int16_t)x_u) * LSB_uT;
    magY = ((int16_t)y_u) * LSB_uT;
    magZ = ((int16_t)z_u) * LSB_uT;

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
        if (echoDuration1 > 25000)
        {
            echoDuration1 = -1; // Timeout, no echo received
        }
        else if (echoDuration1 < 100)
        {
            echoDuration1 = -2; // Too close, likely noise
        }
        else
        {
            echoDuration1 = (int32_t)duration;
        }
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
        if (echoDuration2 > 25000)
        {
            echoDuration2 = -1; // Timeout, no echo received
        }
        else if (echoDuration2 < 100)
        {
            echoDuration2 = -2; // Too close, likely noise
        }
        else
        {
            echoDuration2 = (int32_t)duration;
        }
    }
}

bool setup_tof()
{
    if (!takeI2CMutex(pdMS_TO_TICKS(20)))
    {
        return false;
    }

    bool on = lox.begin();

    if (!on)
    {
        xSemaphoreGive(i2c_mutex);
        return false;
    }

    lox.setMeasurementTimingBudgetMicroSeconds(33000); // 33 ms timing budget
    lox.startRangeContinuous(TOF_TIMING_BUDGET);

    xSemaphoreGive(i2c_mutex);
    return true;
}

void getToFDistance(float &distanceFront)
{
    if (!takeI2CMutex(pdMS_TO_TICKS(10)))
    {
        return;
    }

    VL53L0X_RangingMeasurementData_t measure;
    lox.rangingTest(&measure, false);

    if (measure.RangeStatus != 4)
    {                                                    // 4 = out of range
        distanceFront = measure.RangeMilliMeter / 10.0f; // Convert to cm
    }
    else
    {
        distanceFront = -1.0f; // Indicate out of range
    }

    xSemaphoreGive(i2c_mutex);
}