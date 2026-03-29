// globals.h
#pragma once
#include "types.h"
#include "freertos/semphr.h"
#include "freertos/queue.h"
#include "driver/pcnt.h"
#include "PID.h"
#include <atomic>

extern RobotState robot_state;
extern SemaphoreHandle_t state_mutex;
extern SemaphoreHandle_t i2c_mutex;
extern std::atomic<bool> motorsEnabled;
extern std::atomic<uint32_t> lastMotorCommandMs;
extern PIDController pidLeft;
extern PIDController pidRight;
extern QueueHandle_t commandQueue;
extern pcnt_unit_t pcnt_unit_left;
extern pcnt_unit_t pcnt_unit_right;
extern std::atomic<uint8_t> pageIndex;
extern std::atomic<float> distanceFront;
extern std::atomic<uint8_t> pendingPIDMode; // 0 = PID control mode, 1 = open-loop PWM control mode