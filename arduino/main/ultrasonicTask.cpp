#include "sensors.h"
#include "config.h"

void ultrasonicTask(void *pvParameters) {
    const TickType_t xFrequency = pdMS_TO_TICKS(ULTRASONIC_INTERVAL);
    TickType_t xLastWakeTime = xTaskGetTickCount();
    while (true) {
        triggerUltrasonicPulse1();
        triggerUltrasonicPulse2();
        vTaskDelayUntil(&xLastWakeTime, xFrequency);
    }
}