#include "encoders.h"
#include "driver/pcnt.h"
#include "config.h"
#include "globals.h"

pcnt_unit_t pcnt_unit_left  = PCNT_UNIT_0;
pcnt_unit_t pcnt_unit_right = PCNT_UNIT_1;

void setupEncoderLeft() {
    pcnt_config_t pcnt_config = {};
    pcnt_config.pulse_gpio_num = ENCODER_LEFT_A;
    pcnt_config.ctrl_gpio_num = ENCODER_LEFT_B;
    pcnt_config.channel = PCNT_CHANNEL_0;
    pcnt_config.unit = pcnt_unit_left;
    pcnt_config.pos_mode = PCNT_COUNT_INC;   // Count up on rising edge
    pcnt_config.neg_mode = PCNT_COUNT_DEC;   // Count down on falling edge
    pcnt_config.lctrl_mode = PCNT_MODE_KEEP; // Don't change on control signal
    pcnt_config.hctrl_mode = PCNT_MODE_REVERSE; // Reverse count direction on control high
    pcnt_config.counter_h_lim = 32767;
    pcnt_config.counter_l_lim = -32768;
    pcnt_unit_config(&pcnt_config);
    pcnt_set_filter_value(pcnt_unit_left, 1000);
    pcnt_filter_enable(pcnt_unit_left);

    pcnt_counter_pause(pcnt_unit_left);
    pcnt_counter_clear(pcnt_unit_left);
    pcnt_counter_resume(pcnt_unit_left);
}

void setupEncoderRight() {
    pcnt_config_t pcnt_config = {};
    pcnt_config.pulse_gpio_num = ENCODER_RIGHT_A;
    pcnt_config.ctrl_gpio_num = ENCODER_RIGHT_B;
    pcnt_config.channel = PCNT_CHANNEL_0;
    pcnt_config.unit = PCNT_UNIT_1;
    pcnt_config.pos_mode = PCNT_COUNT_INC;   // Count up on rising edge
    pcnt_config.neg_mode = PCNT_COUNT_DEC;   // Count down on falling edge
    pcnt_config.lctrl_mode = PCNT_MODE_KEEP; // Don't change on control signal
    pcnt_config.hctrl_mode = PCNT_MODE_REVERSE; // Reverse count direction on control high
    pcnt_config.counter_h_lim = 32767;
    pcnt_config.counter_l_lim = -32768;
    pcnt_unit_config(&pcnt_config);
    pcnt_set_filter_value(pcnt_unit_right, 1000);
    pcnt_filter_enable(pcnt_unit_right);

    pcnt_counter_pause(pcnt_unit_right);
    pcnt_counter_clear(pcnt_unit_right);
    pcnt_counter_resume(pcnt_unit_right);
}