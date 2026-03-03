#include <Adafruit_SSD1306.h>
#include <Adafruit_GFX.h>
#include <Wire.h>
#define WIDTH 128
#define HEIGHT 64

Adafruit_SSD1306 display(WIDTH, HEIGHT, &Wire, -1);
static uint32_t last_blink = 0;
static bool blink_state = false;
static uint32_t last_oled_update = 0;
uint16_t elapsed_ms = 0;
uint16_t prev_elapsed_ms = 0;

void setup() {
  Serial.begin(115200);

  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) { // Address 0x3D for 128x64
    Serial.println(F("SSD1306 allocation failed"));
    for(;;);
  }
  delay(2000);
  display.clearDisplay();

  display.setTextSize(1.5);
  display.setTextColor(WHITE);
  display.setCursor(0, 10);

  display.println("[RUN]");
  display.drawLine(0, 20, 127, 20, WHITE);


  // Display static text
  display.setCursor(0, 30);
  display.println("STATUS: OK");
  display.display(); 
}

void loop() {
   uint32_t loop_start = micros();
    
  
  delay(5);
    
  if (millis() - last_blink >= 500) {
    blink_state = !blink_state;
    last_blink = millis();
  }

  if (blink_state) {
      display.fillCircle(45, 13, 3, SSD1306_WHITE);
  } else {
      display.fillCircle(45, 13, 3, SSD1306_BLACK);  // draws black = erases
  }

  if (millis() - last_oled_update >= 100) {
    display.setCursor(60, 10);
    display.fillRect(60, 10, 30, 10, BLACK);
    display.setTextColor(WHITE);
    display.println(String(elapsed_ms) + "ms");

    display.setCursor(90, 10);
    display.println("[~~]");
    display.display();
    last_oled_update = millis();
  }

    uint32_t loop_time = micros() - loop_start;
    
    // enforce 10ms timing
    prev_elapsed_ms = elapsed_ms;
    elapsed_ms = loop_time / 1000;
    if (elapsed_ms < 10) delay(10 - elapsed_ms);

}
