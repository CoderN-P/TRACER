#include "PID.h"
#include "config.h"
#include <cmath>
#include <algorithm>

PIDController::PIDController(float kp, float ki, float kd)
{
    this->pendingKp.store(kp);
    this->pendingKi.store(ki);
    this->pendingKd.store(kd);
    this->setpoint = 0;
    this->pendingSetpoint.store(0);
    this->lastError = 0;
    this->prevInput = 0;
    this->integral = 0;
}

void PIDController::setPendingPIDConstants(float kp, float ki, float kd)
{
    this->pendingKp.store(kp);
    this->pendingKi.store(ki);
    this->pendingKd.store(kd);
}

void PIDController::setSetpoint(float setpoint)
{
    this->setpoint = setpoint;
}

void PIDController::setPendingSetpoint(float pendingSetpoint)
{
    this->pendingSetpoint.store(pendingSetpoint);
}

float PIDController::getSetpoint()
{
    return this->setpoint;
}

float PIDController::getPendingSetpoint()
{
    return this->pendingSetpoint.load();
}

float PIDController::compute(float input, float feedforward)
{
    float _kp = this->pendingKp.load();
    float _ki = this->pendingKi.load();
    float _kd = this->pendingKd.load();
    
    float error = this->setpoint - input;
    
    float proportional_t = _kp * error;
    float derivative_t = _kd * (input - prevInput) / PID_INTERVAL;
    float baseOutput = feedforward + proportional_t - derivative_t;
    
    if (abs(error) < I_ZONE){
        this->integral += error;
    } else {
        this->integral = 0; // Reset integral outside of I_ZONE to prevent windup
    }

    if (_ki > 0)
    {
        float min_i_sum = (-1.0 - baseOutput) / _ki;
        float max_i_sum = (1.0 - baseOutput) / _ki;
        
        if (min_i_sum > max_i_sum){
            float temp = max_i_sum;
            max_i_sum = min_i_sum;
            min_i_sum = temp;
        }
        
        this->integral = std::clamp(this->integral, min_i_sum, max_i_sum);
    }
    
    float integral_t = _ki * integral;
    this->lastError = error;
    this->prevInput = input;
    return feedforward + proportional_t + integral_t + derivative_t;
}

void PIDController::reset()
{
    this->lastError = 0;
    this->integral = 0;
    this->setpoint = 0;
    this->prevInput = 0;
}
