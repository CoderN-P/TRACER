// #include "OLED.h"
#include "freertos/FreeRTOS.h"
#include "config.h"
#include "globals.h"

void oledUpdateTask(void *pvParameters) {
    const TickType_t xFrequency = pdMS_TO_TICKS(OLED_UPDATE_INTERVAL);
    TickType_t xLastWakeTime = xTaskGetTickCount();
    
    while (true) {
        vTaskDelayUntil(&xLastWakeTime, xFrequency);
        // updateOLED();
    }
}