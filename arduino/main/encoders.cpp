#include "encoders.h"
#include "driver/pcnt.h"
#include "config.h"
#include "globals.h"

pcnt_unit_t pcnt_unit_left = PCNT_UNIT_0;
pcnt_unit_t pcnt_unit_right = PCNT_UNIT_1;

static void setupQuadratureEncoder(pcnt_unit_t unit, int pinA, int pinB)
{
    pcnt_config_t channelAConfig = {};
    channelAConfig.pulse_gpio_num = pinA;
    channelAConfig.ctrl_gpio_num = pinB;
    channelAConfig.channel = PCNT_CHANNEL_0;
    channelAConfig.unit = unit;
    channelAConfig.pos_mode = PCNT_COUNT_INC;
    channelAConfig.neg_mode = PCNT_COUNT_DEC;
    channelAConfig.lctrl_mode = PCNT_MODE_KEEP;
    channelAConfig.hctrl_mode = PCNT_MODE_REVERSE;
    channelAConfig.counter_h_lim = 32767;
    channelAConfig.counter_l_lim = -32768;
    pcnt_unit_config(&channelAConfig);

    pcnt_config_t channelBConfig = {};
    channelBConfig.pulse_gpio_num = pinB;
    channelBConfig.ctrl_gpio_num = pinA;
    channelBConfig.channel = PCNT_CHANNEL_1;
    channelBConfig.unit = unit;
    channelBConfig.pos_mode = PCNT_COUNT_DEC;
    channelBConfig.neg_mode = PCNT_COUNT_INC;
    channelBConfig.lctrl_mode = PCNT_MODE_KEEP;
    channelBConfig.hctrl_mode = PCNT_MODE_REVERSE;
    channelBConfig.counter_h_lim = 32767;
    channelBConfig.counter_l_lim = -32768;
    pcnt_unit_config(&channelBConfig);

    pcnt_set_filter_value(unit, 1000);
    pcnt_filter_enable(unit);

    pcnt_counter_pause(unit);
    pcnt_counter_clear(unit);
    pcnt_counter_resume(unit);
}

void setupEncoderLeft()
{
    setupQuadratureEncoder(pcnt_unit_left, ENCODER_LEFT_A, ENCODER_LEFT_B);
}

void setupEncoderRight()
{
    setupQuadratureEncoder(pcnt_unit_right, ENCODER_RIGHT_A, ENCODER_RIGHT_B);
}