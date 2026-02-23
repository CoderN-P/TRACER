#include "PID.h"


PIDController::PIDController(float kp, float ki, float kd, float maxIntegral) {
    this->kp = kp;
    this->ki = ki;
    this->kd = kd;
    this->maxIntegral = maxIntegral;
    this->setpoint = 0;
    this->lastError = 0;
    this->integral = 0;
}

void PIDController::setSetpoint(float setpoint) {
    this->setpoint = setpoint;
}

float PIDController::compute(float input){
    float error = this->setpoint - input;
    this->integral += error;
    this->integral = constrain(this->integral, -maxIntegral, maxIntegral);
    
    float proportional_t = kp*error;
    float integral_t = ki*integral;
    float derivative_t = kd*(error - lastError)/PID_INTERVAL;
    
    this.lastError = error;
    
    return proportional_t + integral_t + derivative_t; 
}
void reset(){
    this.lastError = 0;
    this.integral = 0;
    this.setpoint = 0;
}