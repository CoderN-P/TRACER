#include "OLED.h"
#include "freertos/FreeRTOS.h"
#include "config.h"
#include "globals.h"

void oledUpdateTask(void *pvParameters) {
    const TickType_t xFrequency = pdMS_TO_TICKS(OLED_UPDATE_INTERVAL);
    TickType_t xLastWakeTime = xTaskGetTickCount();
    
    while (true) {
        vTaskDelayUntil(&xLastWakeTime, xFrequency);
        
        RobotState currentState;
        
        if (xSemaphoreTake(state_mutex, pdMS_TO_TICKS(10)) == pdTRUE) {
            currentState = robot_state; // Make a local copy to minimize time holding the mutex
            xSemaphoreGive(state_mutex);
        } else {
            continue; // Skip this update if we can't get the mutex
        }
        
        updateOLED(currentState);
    }
}