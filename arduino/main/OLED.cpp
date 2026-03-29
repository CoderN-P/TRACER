#include "OLED.h"
#include <Adafruit_SSD1306.h>
#include <Adafruit_GFX.h>
#include <Wire.h>
#include "types.h"
#include "globals.h"
#include "config.h"
#include <Arduino.h>
#include <atomic>

uint32_t lastPageSwitch = 0;
std::atomic<uint8_t> pageIndex{0};
bool blinkState = false;
Adafruit_SSD1306 display(OLED_WIDTH, OLED_HEIGHT, &Wire, -1);

bool setupOLED()
{
  // No mutex needed—runs in setup() before FreeRTOS tasks start
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C))
  { // Address 0x3C for 128x64
    return false;
  }

  display.clearDisplay();
  drawHeaderStatic();
  display.display();

  lastPageSwitch = millis();

  return true;
}

void drawHeaderStatic()
{
  display.drawLine(0, DIVIDER_Y, WIDTH - 1, DIVIDER_Y, WHITE);
}

void drawHeader(RobotState &state, bool blinkState)
{
  // Blink dot (status indicator)
  // Draw black rect to clear prev status

  display.setTextSize(1);
  display.setTextColor(WHITE);
  display.fillRect(0, 1, 40, 12, BLACK);
  display.setCursor(0, 4);
  
  bool enabled = motorsEnabled.load();
  
  display.print(enabled ? "[RUN]" : "[STOP]");

  bool motorsPhysical = digitalRead(STBY) == HIGH;

  if (motorsPhysical != enabled)
  {
    display.print("*"); // indicate mismatch between desired and actual motor state
  }

  // Indicate PWM vs PID mode
  if (state.pidMode == 1)
  {
    display.print("-");
  }
  else
  {
    display.print("+");
  }

  display.fillCircle(45, 7, 3, blinkState ? WHITE : BLACK);

  // Loop time
  display.fillRect(52, 1, 30, 12, BLACK);
  display.setTextSize(1);
  display.setCursor(52, 4);
  display.print(state.mainLoopElapsedMs);
  display.print("ms");

  // Battery icon + percentage
  display.fillRect(95, 1, 38, 12, BLACK);
  display.setCursor(95, 4);
  display.print(state.batteryPercent);
  display.print("%");
  display.drawRect(112, 2, 13, 9, WHITE); // battery body
  display.fillRect(125, 4, 3, 5, WHITE);  // battery nub
  // Fill proportional to charge
  uint8_t fillW = (uint8_t)(11 * state.batteryPercent / 100);
  if (fillW)
    display.fillRect(113, 3, fillW, 7, WHITE);
}

void clearContent()
{
  display.fillRect(0, CONTENT_Y, WIDTH, HEIGHT - CONTENT_Y, BLACK);
}

void drawPageDots()
{
  uint8_t idx = pageIndex.load();
  for (uint8_t i = 0; i < NUM_PAGES; i++)
  {
    uint8_t dx = WIDTH - NUM_PAGES * 8 + i * 8;
    if (i == idx)
      display.fillCircle(dx, HEIGHT - 3, 2, WHITE);
    else
      display.drawCircle(dx, HEIGHT - 3, 2, WHITE);
  }
}

// Page 1 ─ Motor PWM bars + velocity
void drawPage1(RobotState &state)
{
    const uint8_t BAR_W = 57;
    const uint8_t BAR_H = 9;
    const uint8_t ROW1_Y = CONTENT_Y + 1;
    const uint8_t BAR_Y = ROW1_Y + 10;
    const uint8_t VEL_Y = BAR_Y + BAR_H + 4;
    const uint8_t SETPOINT_Y = VEL_Y + 10;
    
    
    display.setTextSize(1);
    
    // Labels
    display.setCursor(0, ROW1_Y);
    display.print("L:");
    display.print((int)(state.leftPWM * 100));
    display.print("%");
    display.setCursor(65, ROW1_Y);
    display.print("R:");
    display.print((int)(state.rightPWM * 100));
    display.print("%");
    
    // Left bar (outline + fill)
    display.drawRect(0, BAR_Y, BAR_W, BAR_H, WHITE);
    display.fillRect(0, BAR_Y, (int)(BAR_W * abs(state.leftPWM)), BAR_H, WHITE);
    
    // Right bar
    display.drawRect(65, BAR_Y, BAR_W, BAR_H, WHITE);
    display.fillRect(65, BAR_Y, (int)(BAR_W * abs(state.rightPWM)), BAR_H, WHITE);
    
    // Velocity
    display.setCursor(0, VEL_Y);
    display.print(state.leftSpeed, 3);
    display.print(" m/s");
    display.setCursor(65, VEL_Y);
    display.print(state.rightSpeed, 3);
    display.print(" m/s");
    
    // Setpoints
    display.setCursor(0, SETPOINT_Y);
    display.print(state.leftSetpoint, 3);
    display.print(state.pidMode == 0 ? " m/s" : " PWM");
    display.setCursor(65, SETPOINT_Y);
    display.print(state.rightSetpoint, 3);
    display.print(state.pidMode == 0 ? " m/s" : " PWM");
}

// Page 2 ─ Two lines of text (messages / errors)
void drawPage2(RobotState &state)
{
  display.setTextSize(1);
  display.setCursor(0, CONTENT_Y + 2);

  display.println(state.oledLine1);
  display.setCursor(0, CONTENT_Y + 22);
  display.println(state.oledLine2);
}

// Page 3 ─ ToF + dual ultrasonic
void drawPage3(RobotState &state, bool blinkState)
{
  const uint8_t Y0 = CONTENT_Y + 1;

  display.setTextSize(1);

  // ── ToF sensor ───────────────────────────────────────────
  const float tofDist = state.distanceFront;
  bool warn = (tofDist < TOF_WARN_CM);

  display.setCursor(0, Y0);
  display.print("ToF:");

  if (warn)
  {
    // Flashing inverse "WARN" block
    if (blinkState)
    {
      display.fillRect(26, Y0 - 1, 34, 10, WHITE);
      display.setTextColor(BLACK);
      display.setCursor(28, Y0);
      display.print("WARN");
      display.setTextColor(WHITE);
    }
    // distance in bold
    display.setCursor(65, Y0);
    display.print(tofDist, 1);
    display.print("cm !");
  }
  else
  {
    display.setCursor(26, Y0);
    display.print(tofDist, 1);
    display.print(" cm");
    // Simple proximity bar (max range mapped to 100 cm)
    uint8_t barFill = (uint8_t)(45.0f * min(tofDist, 100.0f) / 100.0f);
    display.drawRect(75, Y0, 45, 8, WHITE);
    display.fillRect(75, Y0, barFill, 8, WHITE);
  }

  // ── Ultrasonic 1 ─────────────────────────────────────────
  display.setCursor(0, Y0 + 14);
  display.print("US1:");
  display.setCursor(26, Y0 + 14);
  if (state.distance1 < 0)
    display.print("--  cm");
  else
  {
    display.print(state.distance1, 1);
    display.print(" cm");
  }

  // ── Ultrasonic 2 ─────────────────────────────────────────
  display.setCursor(0, Y0 + 26);
  display.print("US2:");
  display.setCursor(26, Y0 + 26);
  if (state.distance2 < 0)
    display.print("--  cm");
  else
  {
    display.print(state.distance2, 1);
    display.print(" cm");
  }

  display.setCursor(0, HEIGHT - 8);
  display.print("IR F:");
  display.print(state.irFront ? "T" : "F");
  display.print(" B:");
  display.print(state.irBack ? "T" : "F");
}

void updateOLED(RobotState &state)
{
  // Hold mutex for entire draw+display cycle to prevent I2C buffer corruption
  if (i2c_mutex == NULL || xSemaphoreTake(i2c_mutex, pdMS_TO_TICKS(50)) != pdTRUE)
  {
    return; // Skip this frame if we can't get the lock
  }

  uint32_t now = millis();
  
  uint8_t idx = pageIndex.load();
  
  if (now - lastPageSwitch >= PAGE_CYCLE_MS)
  {
    pageIndex.store((idx + 1) % NUM_PAGES);
    lastPageSwitch = now;
  }

  // 500 ms blink tick (same as oled update interval)
  blinkState = !blinkState;

  clearContent();

  switch (idx)
  {
  case 0:
    drawPage1(state);
    break;
  case 1:
    drawPage2(state);
    break;
  case 2:
    drawPage3(state, blinkState);
    break;
  }

  drawPageDots();
  drawHeader(state, blinkState);

  display.display();
  xSemaphoreGive(i2c_mutex);
}