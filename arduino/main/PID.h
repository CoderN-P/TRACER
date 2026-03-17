#ifndef PID_H
#define PID_H

#define PID_FREQ 100 // PID loop frequency in Hz
#define PID_INTERVAL (1000.0f / PID_FREQ) // PID loop interval in milliseconds

class PIDController {
    private: 
        float kp, ki, kd;
        float setpoint;
        float pwmSetpoint;
        float lastError;
        int mode; // 0 = PID control mode, 1 = open-loop PWM control mode
        float integral;
    public:
        PIDController(float kp, float ki, float kd);
        void reset();     
        float getSetpoint(); // Get the current setpoint of the PID controller
        int getMode(); // Get the current mode (PID control or open-loop PWM control)
        void setPWMSetpoint(float pwmSetpoint); // Set the desired PWM setpoint for feedforward calculation
        float getPWMSetpoint(); // Get the current PWM setpoint (returns 0 if in PID control mode)
        void setSetpoint(float setpoint); // Set the desired setpoint for the PID controller
        float compute(float input, float feedforward); // Returns required output based on the input and setpoint
};
#endif