#include "PID.h"


PIDController::PIDController(float kp, float ki, float kd) {
    this->kp = kp;
    this->ki = ki;
    this->kd = kd;
    this->setpoint = 0;
    this->lastError = 0;
    this->integral = 0;
}

void PIDController::setSetpoint(float setpoint) {
    this->setpoint = setpoint;
    this->integral = 0;
    this->lastError = 0;
}

void PIDController::getSetpoint() {
    return this->setpoint;
}

float PIDController::compute(float input, float feedforward) {
    float error = this->setpoint - input;
    this->integral += error;
    
    float integral_max = 1 - std::abs(feedforward + this->kp*error); // Max integral contribution to avoid windup
    this->integral = constrain(this->integral, -maxIntegral, maxIntegral);
    
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
}