#ifndef OLED_H
#define OLED_H

#include <Adafruit_SSD1306.h>
#include <Adafruit_GFX.h>
#include <Wire.h>
#include "types.h"
#include "globals.h"
#include "config.h"
#include <Arduino.h>

#define WIDTH 128
#define HEIGHT 64

// ── Header region ────────────────────────────────────────────
#define HEADER_H 16  // pixels reserved for the fixed header
#define DIVIDER_Y 15 // y-coord of the horizontal divider line
#define CONTENT_Y 17 // first pixel row of the page content area

// ── Page cycling ─────────────────────────────────────────────
#define NUM_PAGES 3
#define PAGE_CYCLE_MS 5000 // ms between automatic page advances

#define TOF_WARN_CM 20.0f


static uint32_t last_blink = 0;
static bool blink_state = false;
static uint32_t last_oled_update = 0;
static uint8_t page_number = 0;

bool setupOLED();
void drawPageDots();
void clearContent();
void drawHeaderStatic();
void drawPage1(RobotState &state);
void drawPage2(RobotState &state);
void drawPage3(RobotState &state, bool blinkState);
void updateOLED(RobotState &state);
void drawHeader(RobotState &state, bool blinkState);

#endif