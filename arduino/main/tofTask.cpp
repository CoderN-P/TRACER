#include "sensors.h"
#include "config.h"
#include "globals.h"
#include <atomic>

std::atomic<int16_t> distanceFront{3000}; // Initialize with max range (3000 mm for VL53L0X)

void tofTask(void *pvParameters) {
    const TickType_t xFrequency = pdMS_TO_TICKS(TOF_INTERVAL);
    TickType_t xLastWakeTime = xTaskGetTickCount();
    
    while (true) {
        vTaskDelayUntil(&xLastWakeTime, xFrequency);
        int16_t dist;
        getToFDistance(dist);
        distanceFront.store(dist);
    }
}