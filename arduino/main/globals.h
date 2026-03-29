// globals.h
#pragma once
#include "types.h"
#include "freertos/semphr.h"
#include "freertos/queue.h"
#include "driver/pcnt.h"
#include "PID.h"

extern RobotState robot_state;
extern SemaphoreHandle_t state_mutex;
extern SemaphoreHandle_t i2c_mutex;
extern volatile bool motorsEnabled;
extern PIDController pidLeft;
extern PIDController pidRight;
extern QueueHandle_t commandQueue;
extern pcnt_unit_t pcnt_unit_left;
extern pcnt_unit_t pcnt_unit_right;
extern uint8_t pageIndex;
extern float distanceFront;