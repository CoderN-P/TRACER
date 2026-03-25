#include "sensors.h"
#include "config.h"
#include "globals.h"

float distanceFront = 300.0; // Initialize with max range (300 cm for VL53L0X)

void tofTask(void *pvParameters) {
    const TickType_t xFrequency = pdMS_TO_TICKS(TOF_INTERVAL);
    TickType_t xLastWakeTime = xTaskGetTickCount();
    
    while (true) {
        vTaskDelayUntil(&xLastWakeTime, xFrequency);
        getToFDistance(distanceFront);
    }
}