#ifndef PID_H
#define PID_H

#define PID_FREQ 100 // PID loop frequency in Hz
#define PID_INTERVAL (1000 / PID_FREQ) // PID loop interval in milliseconds

class PIDController {
    private: 
        float kp, ki, kd;
        float setpoint;
        float lastError;
        float integral;
    public:
        PIDController(float kp, float ki, float kd);
        
        void setSetpoint(float setpoint); // Set the desired setpoint for the PID controller
        float compute(float input); // Returns required output based on the input and setpoint
};