#include "config.h"
#include "globals.h"
#include "comms.h"

void vSerialTask(void *pvParameters) {
    byte cmdBuf[MAX_BUFFER_SIZE];
    size_t cmdIdx = 0;
    const TickType_t xFrequency = pdMS_TO_TICKS(5); // Check for serial data every 5 ms
    TickType_t xLastWakeTime = xTaskGetTickCount();
    
    while (true) {
        vTaskDelayUntil(&xLastWakeTime, xFrequency);
        uint8_t processed = 0;
    
        while (Serial.available() && processed < MAX_BUFFER_SIZE) {
            processed++;
            uint8_t b = Serial.read();
    
            // reset on overflow before writing
            
            if (cmdIdx >= MAX_BUFFER_SIZE) {
                cmdIdx = 0;
            }
    
            // hunt for start byte
            if (cmdIdx == 0 && b != 0xAA) continue;
    
            cmdBuf[cmdIdx++] = b;
    
            // need at least 2 bytes before checking length
            if (cmdIdx < 2) continue;
    
            uint8_t expected = expectedCommandLength(cmdBuf[1]);
    
            // guard against expectedCommandLength returning 0 or 1
            if (expected < 2) {
                cmdIdx = 0;
                continue;
            }
    
            if (cmdIdx == expected) {
                if (xQueueSend(commandQueue, cmdBuf, 0) != pdPASS) {
                    // Queue full, command lost
                    if (xSemaphoreTake(state_mutex, 0) == pdTRUE) {
                        strncpy(robot_state.oledLine1, "Command Queue", 16);
                        strncpy(robot_state.oledLine2, "Overflow", 16);
                        xSemaphoreGive(state_mutex);
                    }
                }
                cmdIdx = 0;
            }
        }
    }
}