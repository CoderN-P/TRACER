#include "sensors.h"
#include "config.h"

void ultrasonicTask(void *pvParameters) {
    const TickType_t xFrequency = pdMS_TO_TICKS(ULTRASONIC_INTERVAL);
    TickType_t xLastWakeTime = xTaskGetTickCount();
    while (true) {
        vTaskDelayUntil(&xLastWakeTime, xFrequency);
        triggerUltrasonicPulse1();
        
        vTaskDelay(pdMS_TO_TICKS(20)); // Short delay to avoid triggering the second sensor too soon
        
        triggerUltrasonicPulse2();
    }
}