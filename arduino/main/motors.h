#ifndef MOTORS_H
#define MOTORS_H

#include "config.h"
#include "globals.h"
#include "driver/mcpwm.h"
#include "soc/gpio_struct.h"
#include "PID.h"
#include <utility>
#include <Arduino.h>

float getLeftMotorSpeed(int32_t deltaLeftTicks);
float getRightMotorSpeed(int32_t deltaRightTicks);
void setup_pwm();
void handleMovement(float leftPWM, float rightPWM);
void IRAM_ATTR estopISR();
float interpolate(CalibrationPoint_t a, CalibrationPoint_t b, float t);
float compute_left_feedforward(float target);
float compute_right_feedforward(float target);
std::pair<float, float> pidLoop(float leftSpeed, float rightSpeed, uint8_t mode);

#endif