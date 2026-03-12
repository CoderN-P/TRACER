#ifndef OLED_H
#define OLED_H

#include <Adafruit_SSD1306.h>
#include <Adafruit_GFX.h>
#include <Wire.h>
#include "types.h"
#include "globals.h"
#include "config.h"

Adafruit_SSD1306 display(OLED_WIDTH, OLED_HEIGHT, &Wire, -1);
static uint32_t last_blink = 0;
static bool blink_state = false;
static uint32_t last_oled_update = 0;
static uint8_t page_number = 0;

void setupOLED();
void updateOLED();
void drawHeader(RobotState &state);

#endif