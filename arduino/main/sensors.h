#ifndef SENSORS_H
#define SENSORS_H

#include "config.h"
#include "soc/gpio_struct.h"
#include <VL53L0X.h>
#include <Arduino.h>
#include <Wire.h>

extern volatile uint32_t echoStart1;
extern volatile int32_t echoDuration1; // Can be negative to indicate errors: -1 = timeout, -2 = too close
extern volatile uint32_t echoStart2;
extern volatile int32_t echoDuration2; // Can be negative to indicate errors: -1 = timeout, -2 = too close
extern VL53L0X sensor;


bool setup_lsm6dos();
void setup_magnetometer();
void getLSMData(int16_t &ax, int16_t &ay, int16_t &az, int16_t &gx, int16_t &gy, int16_t &gz, int16_t &tempC);
void getMagnetometerData(int16_t &magX, int16_t &magY, int16_t &magZ);
uint8_t getBatteryPercent();
void triggerUltrasonicPulse1();
void triggerUltrasonicPulse2();
void IRAM_ATTR echoISR1();
void IRAM_ATTR echoISR2();
bool setup_tof();
void getToFDistance(int16_t &distance);

#endif