#include "motors.h"
#include "config.h"
#include "globals.h"
#include "driver/mcpwm.h"
#include "soc/gpio_struct.h"
#include "PID.h"
#include <algorithm>
#include <utility>
#include <Arduino.h>
#include <atomic>

std::atomic<uint8_t> pendingPIDMode{0}; // 0 = PID control mode, 1 = open-loop PWM control mode

float getLeftMotorSpeed(int32_t deltaLeftTicks, GeneralConfig cfg)
{
    float deltaLeft;
    if (deltaLeftTicks <= 0){
        deltaLeft = deltaLeftTicks * METERS_PER_TICK * cfg.leftCorrectionNeg;
    } else {
        deltaLeft = deltaLeftTicks * METERS_PER_TICK * cfg.leftCorrectionPos;
    }
    return deltaLeft / (MAIN_INTERVAL / 1000.0); // Convert to m/s
}

float getRightMotorSpeed(int32_t deltaRightTicks, GeneralConfig cfg)
{
    float deltaRight;
    if (deltaRightTicks <= 0){
        deltaRight = deltaRightTicks * METERS_PER_TICK * cfg.rightCorrectionNeg;
    } else {
        deltaRight = deltaRightTicks * METERS_PER_TICK * cfg.rightCorrectionPos;
    }
    return deltaRight / (MAIN_INTERVAL / 1000.0); // Convert to m/s
}

void setup_pwm()
{
    mcpwm_config_t pwm_config;

    pwm_config.frequency = 20000; // 20 kHz motor PWM
    pwm_config.cmpr_a = 0;        // duty cycle A
    pwm_config.cmpr_b = 0;        // duty cycle B
    pwm_config.counter_mode = MCPWM_UP_COUNTER;
    pwm_config.duty_mode = MCPWM_DUTY_MODE_0;

    mcpwm_gpio_init(MCPWM_UNIT_0, MCPWM0A, EN1); // EN1 controls the left motor, which is on operator A of timer 0
    mcpwm_init(MCPWM_UNIT_0, MCPWM_TIMER_0, &pwm_config);
    
    mcpwm_gpio_init(MCPWM_UNIT_0, MCPWM1A, EN2); // EN2 controls the right motor, which is on operator A of timer 1
    mcpwm_init(MCPWM_UNIT_0, MCPWM_TIMER_1, &pwm_config);
    
}

void handleMovement(float left, float right)
{
    // Values already mapped between -1 and 1, so just need to scale to float percentage
    // Clamp the speeds to the valid range just in case

    float leftSpeed = constrain(left, -MAX_PWM, MAX_PWM);
    float rightSpeed = constrain(right, -MAX_PWM, MAX_PWM);
    
    bool enabled = motorsEnabled.load();

    if (leftSpeed > 0 && enabled)
    {
        digitalWrite(IN1, HIGH);
        digitalWrite(IN2, LOW);
        mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_A, leftSpeed * 100.0);
    }
    else if (leftSpeed < 0 && enabled)
    {
        digitalWrite(IN1, LOW);
        digitalWrite(IN2, HIGH);
        mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_A, -leftSpeed * 100.0);
    }
    else
    {
        digitalWrite(IN1, HIGH);
        digitalWrite(IN2, HIGH);
        
        mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_A, 0.0);
    }

    if (rightSpeed > 0 && enabled)
    {
        // Swapped high and low for wiring
        digitalWrite(IN3, LOW);
        digitalWrite(IN4, HIGH);
        mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_1, MCPWM_OPR_A, rightSpeed * 100.0);
    }
    else if (rightSpeed < 0 && enabled)
    {
        digitalWrite(IN3, HIGH);
        digitalWrite(IN4, LOW);
        mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_1, MCPWM_OPR_A, -rightSpeed * 100.0);
    }
    else
    {
        digitalWrite(IN3, HIGH);
        digitalWrite(IN4, HIGH);

        mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_1, MCPWM_OPR_A, 0.0);
    }
}

void IRAM_ATTR estopISR()
{
    motorsEnabled = !motorsEnabled;
    if (motorsEnabled){
        GPIO.out_w1ts = (1ULL << STBY);
    } else {
        GPIO.out_w1tc = (1ULL << STBY);
    }
}

float interpolate(CalibrationPoint_t a, CalibrationPoint_t b, float t){
    if (t <= a.input) return a.output;
    if (t >= b.input) return b.output;
    
    float ratio = (t - a.input) / (b.input - a.input);
    return a.output + ratio * (b.output - a.output);
}

float compute_left_feedforward(float target){
    if (target > 0){
        for (int i = 1; i < LOOKUP_TABLE_SIZE; i++){
            CalibrationPoint_t a = calibration_forward_left[i-1];
            CalibrationPoint_t b = calibration_forward_left[i];
            
            if (target < a.input) break;
            
            if (target >= a.input && target <= b.input){
                return interpolate(a, b, target);
            }
        }
    } else {
        for (int i = 1; i < LOOKUP_TABLE_SIZE; i++){
            CalibrationPoint_t a = calibration_backward_left[i-1];
            CalibrationPoint_t b = calibration_backward_left[i];
            
            if (target < a.input) break;
            
            if (target >= a.input && target <= b.input){
                return interpolate(a, b, target);
            }
        }
    }
    
    return 0;
}

float compute_right_feedforward(float target){
    if (target > 0){
        for (int i = 1; i < LOOKUP_TABLE_SIZE; i++){
            CalibrationPoint_t a = calibration_forward_right[i-1];
            CalibrationPoint_t b = calibration_forward_right[i];
            
            if (target < a.input) break;
            
            if (target >= a.input && target <= b.input){
                return interpolate(a, b, target);
            }
        }
    } else {
        for (int i = 1; i < LOOKUP_TABLE_SIZE; i++){
            CalibrationPoint_t a = calibration_backward_right[i-1];
            CalibrationPoint_t b = calibration_backward_right[i];
            
            if (target < a.input) break;
            
            if (target >= a.input && target <= b.input){
                return interpolate(a, b, target);
            }
        }
    }
    
    return 0;
}

float getTrackWidthFromCurvature(float curvature){
    return MAX_WHEEL_BASE - (MAX_WHEEL_BASE - MIN_WHEEL_BASE) * exp(-ALPHA * abs(curvature));
}

std::pair<float, float> scaleToMax(float left, float right, GeneralConfig cfg){
    float left_limit = cfg.maxLinearVelPos;
    float right_limit = cfg.maxLinearVelPos;
    
    if (left < 0) left_limit = cfg.maxLinearVelNeg;
    if (right < 0) right_limit = cfg.maxLinearVelNeg;

    float left_scale = 1.0; 
    float right_scale = 1.0;
    if (abs(left) > 0) left_scale = left_limit / abs(left);
    if (abs(right) > 0) right_scale = right_limit / abs(right);

    float scale = std::min(left_scale, right_scale);
    scale = std::min(scale, 1.0f);
    
    float scaled_left = left * scale;
    float scaled_right = right * scale;
    
    float final_left = constrain(scaled_left, -cfg.maxLinearVelNeg, cfg.maxLinearVelPos);
    float final_right = constrain(scaled_right, -cfg.maxLinearVelNeg, cfg.maxLinearVelPos);

    return {final_left, final_right};
}

float getTrackWidth(float v, float omega, GeneralConfig cfg){
    float w_eff;
        
    if (cfg.useAdaptiveWheelBase){
        float curvature;
        if (abs(v) > 1e-5){
            curvature = omega / v;
        } else {
            curvature = 0;
        }
        w_eff = getTrackWidthFromCurvature(curvature);
    } else {
        w_eff = cfg.nominalWheelBase;
    }
    return w_eff;
}
std::pair<float, float> twistToWheelSpeeds(float v, float omega, float w, GeneralConfig cfg) {
    float left = v - (omega * w / 2.0);
    float right = v + (omega * w / 2.0);
    
    return scaleToMax(left, right, cfg);
}

float getOmega(float vl, float vr, float w){
    return (vr - vl) / w;
}

std::pair<float, float> pidLoop(float leftSpeed, float rightSpeed, uint8_t mode, float omega, GeneralConfig cfg)
{
    // Simple feedforward model

    // Only run direct PWM control if the PWM values are set and in range. As soon as a motor command is recieved, the PWM setpoint will be set to 2 (out of range) to indicate that we should be in PID control mode, so this allows us to switch between open-loop PWM control and closed-loop PID control based on whether we've received a valid motor command or not.
    if (mode == 1)
    {
        // If we're in open-loop PWM control mode, just return the PWM setpoint as the output without PID correction
        handleMovement(pidLeft.getSetpoint(), pidRight.getSetpoint());
        return {pidLeft.getSetpoint(), pidRight.getSetpoint()};
    }
    
    float leftSetpoint = pidLeft.getPendingSetpoint();
    float rightSetpoint = pidRight.getPendingSetpoint();
    
    if (cfg.useGyroCorrection) {
        float wheelCorrection;
        if (mode == 2){
            float targetOmega = rightSetpoint;
            float w;
            
            if (cfg.useAdaptiveWheelBase){
                w = getTrackWidth(leftSetpoint, rightSetpoint, cfg);
            } else {
                w = cfg.nominalWheelBase;
            }
            std::tie(leftSetpoint, rightSetpoint) = twistToWheelSpeeds(leftSetpoint, rightSetpoint, w, cfg);
            float omegaError = targetOmega - omega;
            float correction = cfg.omegaP * omegaError;
            wheelCorrection = correction * w / 2.0;
        } else {
            float targetOmega = getOmega(leftSetpoint, rightSetpoint, cfg.nominalWheelBase);
            float omegaError = targetOmega - omega;
            float correction = cfg.omegaP * omegaError;
            wheelCorrection = correction * cfg.nominalWheelBase / 2.0;
        }
        
        leftSetpoint -= wheelCorrection;
        rightSetpoint += wheelCorrection;
        
        std::tie(leftSetpoint, rightSetpoint) = scaleToMax(leftSetpoint, rightSetpoint, cfg);
    } else {
        if (mode == 2){
            float w;
            if (cfg.useAdaptiveWheelBase){
                w = getTrackWidth(leftSetpoint, rightSetpoint, cfg);
            } else {
                w = cfg.nominalWheelBase;
            }
            std::tie(leftSetpoint, rightSetpoint) = twistToWheelSpeeds(leftSetpoint, rightSetpoint, w, cfg);
        } 
    }
    
    pidLeft.setSetpoint(leftSetpoint);
    pidRight.setSetpoint(rightSetpoint);

    float leftFeedforward = compute_left_feedforward(pidLeft.getSetpoint());
    float rightFeedforward = compute_right_feedforward(pidRight.getSetpoint());

    float outputLeft = constrain(pidLeft.compute(leftSpeed, leftFeedforward, cfg.pLeft, cfg.iLeft, cfg.dLeft, cfg.iZone), -MAX_PWM, MAX_PWM);
    float outputRight = constrain(pidRight.compute(rightSpeed, rightFeedforward, cfg.pRight, cfg.iRight, cfg.dRight, cfg.iZone), -MAX_PWM, MAX_PWM);

    handleMovement(outputLeft, outputRight);

    return {outputLeft, outputRight};
}