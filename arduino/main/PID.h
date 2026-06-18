#ifndef PID_H
#define PID_H

#define PID_FREQ 200                      // PID loop frequency in Hz
#define PID_INTERVAL (1000.0f / PID_FREQ) // PID loop interval in milliseconds

#include <atomic>
#include "config.h"

class PIDController
{
private:
    float setpoint;
    std::atomic<float> pendingSetpoint; // For thread-safe setpoint updates from the command processor task
    float lastError;
    float integral;
    float prevInput;
public:
    PIDController();
    void reset();
    float getSetpoint();                            // Get the current setpoint of the PID controller
    void setPendingSetpoint(float pendingSetpoint); // Set the desired setpoint for the PID controller
    float getPendingSetpoint();                     // Get the current PWM setpoint (returns 0 if in PID control mode)
    void setSetpoint(float setpoint);               // Set the desired setpoint for the PID controller
    float compute(float input, float feedforward, float _kp, float _ki, float _kd);  // Returns required output based on the input and setpoint
};
#endif
