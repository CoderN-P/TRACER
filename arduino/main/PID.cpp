#include "PID.h"
#include <cmath>
#include <algorithm>


PIDController::PIDController(float kp, float ki, float kd) {
    this->kp = kp;
    this->ki = ki;
    this->kd = kd;
    this->setpoint = 0;
    this->lastError = 0;
    this->integral = 0;
    this->pwmSetpoint = 0;
    this->mode = 0; // 0 = PID control mode, 1 = open-loop PWM control mode
}

void PIDController::setSetpoint(float setpoint) {
    this->setpoint = setpoint;
    this->integral = 0;
    this->lastError = 0;
    this->mode = 0; // Switch to PID control mode
    this->pwmSetpoint = 0; 
}

void PIDController::setPWMSetpoint(float pwmSetpoint) {
    this->mode = 1; // Switch to open-loop PWM control mode
    this->pwmSetpoint = pwmSetpoint;
}

int PIDController::getMode() {
    return this->mode;
}

float PIDController::getPWMSetpoint() {
    return this->pwmSetpoint;
}

float PIDController::getSetpoint() {
    return this->setpoint;
}

float PIDController::compute(float input, float feedforward) {
    float error = this->setpoint - input;
    this->integral += error;
    
    if (this->ki > 0) {
        float maxIntegral = (1 - abs(feedforward + this->kp*error)) / this->ki; // Max integral contribution to avoid windup
        this->integral = std::clamp(this->integral, -maxIntegral, maxIntegral);
    }
    float proportional_t = kp*error;
    float integral_t = ki*integral;
    float derivative_t = kd*(error - lastError)/PID_INTERVAL;
    
    this->lastError = error;
    
    return feedforward + proportional_t + integral_t + derivative_t; 
}
void PIDController::reset(){
    this->lastError = 0;
    this->integral = 0;
    this->setpoint = 0;
    this->pwmSetpoint = 0;
    this->mode = 0;
}