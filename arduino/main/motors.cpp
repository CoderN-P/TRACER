#include "motors.h"
#include "config.h"
#include "globals.h"
#include "driver/mcpwm.h"
#include "soc/gpio_struct.h"
#include "PID.h"
#include <utility>
#include <Arduino.h>
#include <atomic>

std::atomic<uint8_t> pendingPIDMode{0}; // 0 = PID control mode, 1 = open-loop PWM control mode

float getLeftMotorSpeed(int32_t deltaLeftTicks)
{
    float deltaLeft = deltaLeftTicks * METERS_PER_TICK_LEFT;
    return deltaLeft / (MAIN_INTERVAL / 1000.0); // Convert to m/s
}

float getRightMotorSpeed(int32_t deltaRightTicks)
{
    float deltaRight = deltaRightTicks * METERS_PER_TICK_RIGHT;
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

    mcpwm_gpio_init(MCPWM_UNIT_0, MCPWM0A, EN1); // EN1 controls the right motor, which is on operator A
    mcpwm_gpio_init(MCPWM_UNIT_0, MCPWM0B, EN2); // EN2 controls the left motor, which is on operator B

    mcpwm_init(MCPWM_UNIT_0, MCPWM_TIMER_0, &pwm_config);
    // mcpwm_set_duty_type(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_A, MCPWM_DUTY_MODE_0);
    // mcpwm_set_duty_type(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_B, MCPWM_DUTY_MODE_0);
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
        digitalWrite(IN3, HIGH);
        digitalWrite(IN4, LOW);
        mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_B, leftSpeed * 100.0);
    }
    else if (leftSpeed < 0 && enabled)
    {
        digitalWrite(IN3, LOW);
        digitalWrite(IN4, HIGH);
        mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_B, -leftSpeed * 100.0);
    }
    else
    {
        if (enabled)
        {
            // Allow motors to coast by setting both IN pins low but keeping PWM enabled at 0 duty cycle}
            digitalWrite(IN3, LOW);
            digitalWrite(IN4, LOW);
        }
        else
        {
            // If motors are disabled, actively brake by setting both IN pins high
            digitalWrite(IN3, HIGH);
            digitalWrite(IN4, HIGH);
        }
        mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_B, 0.0);
    }

    if (rightSpeed > 0 && enabled)
    {
        // Swapped high and low for wiring
        digitalWrite(IN1, LOW);
        digitalWrite(IN2, HIGH);
        mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_A, rightSpeed * 100.0);
    }
    else if (rightSpeed < 0 && enabled)
    {
        digitalWrite(IN1, HIGH);
        digitalWrite(IN2, LOW);
        mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_A, -rightSpeed * 100.0);
    }
    else
    {
        if (enabled)
        {
            // Allow motors to coast by setting both IN pins low but keeping PWM enabled at 0 duty cycle
            digitalWrite(IN1, LOW);
            digitalWrite(IN2, LOW);
        }
        else
        {
            // If motors are disabled, actively brake by setting both IN pins high
            digitalWrite(IN1, HIGH);
            digitalWrite(IN2, HIGH);
        }

        mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_A, 0.0);
    }
}

void IRAM_ATTR estopISR()
{
    motorsEnabled = false;
    GPIO.out_w1tc = (1ULL << STBY);
}

float sign(float v)
{
    if (v > 0)
        return 1.0;
    if (v < 0)
        return -1.0;
    return 0.0;
}

std::pair<float, float> pidLoop(float leftSpeed, float rightSpeed, uint8_t mode)
{
    // Simple feedforward model

    // Only run direct PWM control if the PWM values are set and in range. As soon as a motor command is recieved, the PWM setpoint will be set to 2 (out of range) to indicate that we should be in PID control mode, so this allows us to switch between open-loop PWM control and closed-loop PID control based on whether we've received a valid motor command or not.
    if (mode == 1)
    {
        // If we're in open-loop PWM control mode, just return the PWM setpoint as the output without PID correction
        handleMovement(pidLeft.getSetpoint(), pidRight.getSetpoint());
        return {pidLeft.getSetpoint(), pidRight.getSetpoint()};
    }

    float leftFeedforward = pidLeft.getSetpoint() * kV_LEFT + kS_LEFT * sign(pidLeft.getSetpoint());
    float rightFeedforward = pidRight.getSetpoint() * kV_RIGHT + kS_RIGHT * sign(pidRight.getSetpoint());

    float outputLeft = constrain(pidLeft.compute(leftSpeed, leftFeedforward), -MAX_PWM, MAX_PWM);
    float outputRight = constrain(pidRight.compute(rightSpeed, rightFeedforward), -MAX_PWM, MAX_PWM);

    handleMovement(outputLeft, outputRight);

    return {outputLeft, outputRight};
}