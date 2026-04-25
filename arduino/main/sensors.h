#ifndef SENSORS_H
#define SENSORS_H

#include "config.h"
#include "soc/gpio_struct.h"
#include "Adafruit_VL53L0X.h"
#include <Arduino.h>
#include <Wire.h>

extern volatile uint32_t echoStart1;
extern volatile int32_t echoDuration1; // Can be negative to indicate errors: -1 = timeout, -2 = too close
extern volatile uint32_t echoStart2;
extern volatile int32_t echoDuration2; // Can be negative to indicate errors: -1 = timeout, -2 = too close
extern Adafruit_VL53L0X lox;

bool initMPU6050();
void setup_magnetometer();
void getMPUData(int &ax, int &ay, int &az, int &gx, int &gy, int &gz, float &tempC);
void getMagnetometerData(float &magX, float &magY, float &magZ);
uint8_t getBatteryPercent();
void triggerUltrasonicPulse1();
void triggerUltrasonicPulse2();
void IRAM_ATTR echoISR1();
void IRAM_ATTR echoISR2();
bool setup_tof();
void getToFDistance(float &distance);

#endif