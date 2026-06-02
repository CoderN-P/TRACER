#include "OLED.h"
#include "freertos/FreeRTOS.h"
#include "config.h"
#include "globals.h"

void oledUpdateTask(void *pvParameters) {
    const TickType_t xFrequency = pdMS_TO_TICKS(OLED_UPDATE_INTERVAL);
    TickType_t xLastWakeTime = xTaskGetTickCount();
    
    while (true) {
        RobotState currentState;
        
        if (xSemaphoreTake(state_mutex, pdMS_TO_TICKS(10)) == pdTRUE) {
            currentState = robot_state; // Make a local copy to minimize time holding the mutex
            xSemaphoreGive(state_mutex);
        } else {
            continue; // Skip this update if we can't get the mutex
        }
        
        updateOLED(currentState);
        
        for (int page = 0; page < 8; page++){
            for (int chunk = 0; chunk < 4; chunk++){
                if (xSemaphoreTake(i2c_mutex, portMAX_DELAY) == pdTRUE){
                    send_oled_page(page, chunk);
                    xSemaphoreGive(i2c_mutex);
                }
                vTaskDelay(pdMS_TO_TICKS(6)); // Small delay between page updates to avoid I2C congestion
            }
        }
        
        vTaskDelayUntil(&xLastWakeTime, xFrequency);
                
    }
}