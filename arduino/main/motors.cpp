#include "motors.h"
#include "config.h"
#include "globals.h"
#include "driver/mcpwm.h"
#include "soc/gpio_struct.h"
#include "PID.h"
#include <utility>
#include <Arduino.h>

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

void setup_pwm(){
    mcpwm_config_t pwm_config;
    
    pwm_config.frequency = 20000;     // 20 kHz motor PWM
    pwm_config.cmpr_a = 0;            // duty cycle A
    pwm_config.cmpr_b = 0;            // duty cycle B
    pwm_config.counter_mode = MCPWM_UP_COUNTER;
    pwm_config.duty_mode = MCPWM_DUTY_MODE_0;
    
    mcpwm_gpio_init(MCPWM_UNIT_0, MCPWM0A, EN1);
    mcpwm_gpio_init(MCPWM_UNIT_0, MCPWM0B, EN2);
    
    mcpwm_init(MCPWM_UNIT_0, MCPWM_TIMER_0, &pwm_config);
}


void handleMovement(float left, float right)
{
    // Values already mapped between -1 and 1, so just need to scale to float percentage
    // Clamp the speeds to the valid range just in case
    
    float leftSpeed = constrain(left, -MAX_PWM, MAX_PWM);
    float rightSpeed = constrain(right, -MAX_PWM, MAX_PWM);

    if (leftSpeed > 0 && motorsEnabled)
    {
        digitalWrite(IN1, HIGH);
        digitalWrite(IN2, LOW);
        mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_A, leftSpeed * 100);
        mcpwm_set_duty_type(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_A, MCPWM_DUTY_MODE_0);
    }
    else if (leftSpeed < 0 && motorsEnabled)
    {
        digitalWrite(IN1, LOW);
        digitalWrite(IN2, HIGH);
        mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_A, -leftSpeed * 100);
        mcpwm_set_duty_type(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_A, MCPWM_DUTY_MODE_0);
    }
    else
    {
        digitalWrite(IN1, LOW);
        digitalWrite(IN2, LOW);
        mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_A, 0);
        mcpwm_set_duty_type(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_A, MCPWM_DUTY_MODE_0);
    }

    if (rightSpeed > 0 && motorsEnabled)
    {
        digitalWrite(IN3, HIGH);
        digitalWrite(IN4, LOW);
        mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_B, rightSpeed * 100);
        mcpwm_set_duty_type(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_B, MCPWM_DUTY_MODE_0);
    }
    else if (rightSpeed < 0 && motorsEnabled)
    {
        digitalWrite(IN3, LOW);
        digitalWrite(IN4, HIGH);
        mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_B, -rightSpeed * 100);
        mcpwm_set_duty_type(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_B, MCPWM_DUTY_MODE_0);
    }
    else
    {
        digitalWrite(IN3, LOW);
        digitalWrite(IN4, LOW);
        mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_B, 0);
        mcpwm_set_duty_type(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_OPR_B, MCPWM_DUTY_MODE_0);
    }
}

void IRAM_ATTR estopISR() {
    motorsEnabled = false;
    GPIO.out_w1tc = (1ULL << STBY);
}

std::pair<float, float> pidLoop(float leftSpeed, float rightSpeed){
    // Simple feedforward model 
    float leftFeedforward = pidLeft.getSetpoint() * MAX_PWM / MAX_OUTPUT_SPEED_LEFT;
    float rightFeedforward = pidRight.getSetpoint() * MAX_PWM / MAX_OUTPUT_SPEED_RIGHT;
    
    float outputLeft = constrain(pidLeft.compute(leftSpeed, leftFeedforward), -MAX_PWM, MAX_PWM);
    float outputRight = constrain(pidRight.compute(rightSpeed, rightFeedforward), -MAX_PWM, MAX_PWM);
    
    handleMovement(outputLeft, outputRight);
    
    return {outputLeft, outputRight};
}