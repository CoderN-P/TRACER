#include <Adafruit_SSD1306.h>
#include <Adafruit_GFX.h>
#include <Wire.h>
#include <atomic>

#define WIDTH 128
#define HEIGHT 64

// ── Header region ────────────────────────────────────────────
#define HEADER_H 16  // pixels reserved for the fixed header
#define DIVIDER_Y 15 // y-coord of the horizontal divider line
#define CONTENT_Y 17 // first pixel row of the page content area

// ── Page cycling ─────────────────────────────────────────────
#define NUM_PAGES 3
#define PAGE_CYCLE_MS 5000 // ms between automatic page advances

// ── Hardcoded demo values ─────────────────────────────────────
// Page 1 – motors
float leftPwm = 0.75f; // 0.0 – 1.0
float rightPwm = 0.25f;
float leftVel = 0.576f; // m/s
float rightVel = 0.123f;

// Page 2 – text messages
const char *msgLine1 = "RPi: path loaded";
const char *msgLine2 = "Waiting for start";

// Page 3 – sensors
float tofDist = 18.4f;  // cm  (main ToF sensor)
float us1Dist = 45.2f;  // cm  (ultrasonic 1)
float us2Dist = 112.7f; // cm  (ultrasonic 2)
bool irFront = true;
bool irBack = false;
#define TOF_WARN_CM 20.0f

// ── State ─────────────────────────────────────────────────────
Adafruit_SSD1306 display(WIDTH, HEIGHT, &Wire, -1);

std::atomic<uint8_t> pageIndex = 0;
static uint32_t lastPageSwitch = 0;
static uint32_t lastOledUpdate = 0;
static uint32_t lastBlink = 0;
static bool blinkState = false;
static uint32_t lastFakeUpdate = 0;
static uint16_t simStep = 0;
static uint8_t battPct = 72;
static uint16_t fakeLoopMs = 10;

const char *msgPool1[] = {
    "Path loaded",
    "Tracking",
    "Obstacle near",
    "Replan active",
    "Link stable"};

const char *msgPool2[] = {
    "Await start",
    "Goal update",
    "Speed limited",
    "Recovery mode",
    "Sensors nominal"};

const uint8_t MSG_COUNT = sizeof(msgPool1) / sizeof(msgPool1[0]);

// ── Helpers ───────────────────────────────────────────────────

// Clear only the content area below the header
void clearContent()
{
  display.fillRect(0, CONTENT_Y, WIDTH, HEIGHT - CONTENT_Y, BLACK);
}

// Draw the persistent header (called once on init, then only the
// mutable parts – blink dot, loop time, battery – are refreshed)
void drawHeaderStatic()
{
  display.setTextSize(1);
  display.setTextColor(WHITE);
  display.setCursor(0, 4);
  display.print("[RUN]");
  display.drawLine(0, DIVIDER_Y, WIDTH - 1, DIVIDER_Y, WHITE);
}

void refreshHeader(uint16_t loopMs, uint8_t battPct)
{
  // Blink dot (status indicator)
  display.fillCircle(45, 7, 3, blinkState ? WHITE : BLACK);

  // Loop time
  display.fillRect(52, 1, 30, 12, BLACK);
  display.setTextSize(1);
  display.setCursor(52, 4);
  display.print(loopMs);
  display.print("ms");

  // Battery icon + percentage
  display.fillRect(90, 1, 38, 12, BLACK);
  display.setCursor(90, 4);
  display.print(battPct);
  display.print("%");
  display.drawRect(112, 2, 13, 9, WHITE); // battery body
  display.fillRect(125, 4, 3, 5, WHITE);  // battery nub
  // Fill proportional to charge
  uint8_t fillW = (uint8_t)(11 * battPct / 100);
  if (fillW)
    display.fillRect(113, 3, fillW, 7, WHITE);
}

void drawPageDots()
{
  for (uint8_t i = 0; i < NUM_PAGES; i++)
  {
    uint8_t dx = WIDTH - NUM_PAGES * 8 + i * 8;
    if (i == pageIndex)
      display.fillCircle(dx, HEIGHT - 3, 2, WHITE);
    else
      display.drawCircle(dx, HEIGHT - 3, 2, WHITE);
  }
}

float triWave(uint16_t phase, uint16_t period)
{
  uint16_t p = phase % period;
  uint16_t half = period / 2;
  if (p < half)
  {
    return (float)p / (float)half;
  }
  return (float)(period - p) / (float)half;
}

void updateFakeData(uint32_t now)
{
  if (now - lastFakeUpdate < 120)
  {
    return;
  }
  lastFakeUpdate = now;
  simStep++;

  float tSlow = triWave(simStep, 120);
  float tFast = triWave(simStep * 3, 120);

  leftPwm = 0.22f + 0.70f * tSlow;
  rightPwm = 0.18f + 0.74f * tFast;

  leftVel = 0.10f + leftPwm * 0.95f;
  rightVel = 0.08f + rightPwm * 0.90f;

  tofDist = 9.0f + 55.0f * triWave(simStep * 2, 180);
  us1Dist = 22.0f + 125.0f * triWave(simStep + 25, 200);
  us2Dist = 18.0f + 140.0f * triWave(simStep + 90, 220);

  irFront = (tofDist < 16.0f) || ((simStep / 10) % 9 == 0);
  irBack = ((simStep / 14) % 7 == 0);

  uint8_t msgIdx = (simStep / 16) % MSG_COUNT;
  msgLine1 = msgPool1[msgIdx];
  msgLine2 = msgPool2[msgIdx];

  battPct = 65 + (uint8_t)(12.0f * triWave(simStep, 360));
  fakeLoopMs = 8 + (uint16_t)(5.0f * triWave(simStep * 5, 120));
}

// Page 1 ─ Motor PWM bars + velocity
void drawPage1()
{
  const uint8_t BAR_W = 57;
  const uint8_t BAR_H = 9;
  const uint8_t ROW1_Y = CONTENT_Y + 1;
  const uint8_t BAR_Y = ROW1_Y + 10;
  const uint8_t VEL_Y = BAR_Y + BAR_H + 4;

  display.setTextSize(1);

  // Labels
  display.setCursor(0, ROW1_Y);
  display.print("L:");
  display.print((int)(leftPwm * 100));
  display.print("%");
  display.setCursor(65, ROW1_Y);
  display.print("R:");
  display.print((int)(rightPwm * 100));
  display.print("%");

  // Left bar (outline + fill)
  display.drawRect(0, BAR_Y, BAR_W, BAR_H, WHITE);
  display.fillRect(0, BAR_Y, (int)(BAR_W * leftPwm), BAR_H, WHITE);

  // Right bar
  display.drawRect(65, BAR_Y, BAR_W, BAR_H, WHITE);
  display.fillRect(65, BAR_Y, (int)(BAR_W * rightPwm), BAR_H, WHITE);

  // Velocity
  display.setCursor(0, VEL_Y);
  display.print(leftVel, 3);
  display.print(" m/s");
  display.setCursor(65, VEL_Y);
  display.print(rightVel, 3);
  display.print(" m/s");
}

// Page 2 ─ Two lines of text (messages / errors)
void drawPage2()
{
  display.setTextSize(1.8);
  display.setCursor(0, CONTENT_Y + 2);
  display.println(msgLine1);
  display.setCursor(0, CONTENT_Y + 22);
  display.println(msgLine2);
}

// Page 3 ─ ToF + dual ultrasonic
void drawPage3()
{
  const uint8_t Y0 = CONTENT_Y + 1;

  display.setTextSize(1);

  // ── ToF sensor ───────────────────────────────────────────
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
  if (us1Dist < 0)
    display.print("--  cm");
  else
  {
    display.print(us1Dist, 1);
    display.print(" cm");
  }

  // ── Ultrasonic 2 ─────────────────────────────────────────
  display.setCursor(0, Y0 + 26);
  display.print("US2:");
  display.setCursor(26, Y0 + 26);
  if (us2Dist < 0)
    display.print("--  cm");
  else
  {
    display.print(us2Dist, 1);
    display.print(" cm");
  }

  display.setCursor(0, HEIGHT - 8);
  display.print("IR F:");
  display.print(irFront ? "T" : "F");
  display.print(" B:");
  display.print(irBack ? "T" : "F");
}

// ── Setup ─────────────────────────────────────────────────────
void setup()
{
  Serial.begin(115200);

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C))
  {
    Serial.println(F("SSD1306 allocation failed"));
    for (;;)
      ;
  }

  delay(500);
  display.clearDisplay();
  drawHeaderStatic();
  display.display();

  lastPageSwitch = millis();
}

// ── Loop ──────────────────────────────────────────────────────
void loop()
{
  uint32_t now = millis();

  updateFakeData(now);

  // Advance page every PAGE_CYCLE_MS
  if (now - lastPageSwitch >= PAGE_CYCLE_MS)
  {
    pageIndex = (pageIndex + 1) % NUM_PAGES;
    lastPageSwitch = now;
  }

  // 500 ms blink tick
  if (now - lastBlink >= 500)
  {
    blinkState = !blinkState;
    lastBlink = now;
  }

  // Redraw at ~10 Hz
  if (now - lastOledUpdate >= 100)
  {
    lastOledUpdate = now;

    clearContent();

    switch (pageIndex)
    {
    case 0:
      drawPage1();
      break;
    case 1:
      drawPage2();
      break;
    case 2:
      drawPage3();
      break;
    }

    drawPageDots();

    refreshHeader(fakeLoopMs, battPct);
    display.display();
  }
}