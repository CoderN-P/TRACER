#ifndef PID_H
#define PID_H

#define PID_FREQ 100 // PID loop frequency in Hz
#define PID_INTERVAL (1000.0f / PID_FREQ) // PID loop interval in milliseconds

class PIDController {
    private: 
        float kp, ki, kd;
        float setpoint;
        float lastError;
        float integral;
    public:
        PIDController(float kp, float ki, float kd);
        void reset();     
        float getSetpoint(); // Get the current setpoint of the PID controller
        void setSetpoint(float setpoint); // Set the desired setpoint for the PID controller
        float compute(float input, float feedforward); // Returns required output based on the input and setpoint
};
#endif