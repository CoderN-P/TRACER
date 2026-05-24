#include "PID.h"
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
    this->integral += error;

    if (_ki > 0)
    {
        float maxIntegral = (1 - abs(feedforward + _kp * error)) / _ki; // Max integral contribution to avoid windup
        this->integral = std::clamp(this->integral, -maxIntegral, maxIntegral);
    }
    float proportional_t = _kp * error;
    float integral_t = _ki * integral;
    float derivative_t = _kd * (error - lastError) / PID_INTERVAL;

    this->lastError = error;

    return feedforward + proportional_t + integral_t + derivative_t;
}

void PIDController::reset()
{
    this->lastError = 0;
    this->integral = 0;
    this->setpoint = 0;
}