#include "config.h"
#include "comms.h"
#include "globals.h"

void commandProcessorTask(void *pvParameters) {
    byte buffer[MAX_BUFFER_SIZE];
    
    static uint8_t latestCmds[NUM_TYPES][MAX_BUFFER_SIZE];
    bool typeReceived[NUM_TYPES];
    
    while (true) {
        if (xQueueReceive(commandQueue, buffer, portMAX_DELAY) == pdPASS) {
            memset(typeReceived, 0, sizeof(typeReceived)); // Reset received flags for all command types
            
             // Update the latest command for this type
             
             do {
                uint8_t type = buffer[1]; // Command byte is the second byte (after start byte)
                
                int typeIndex = getTypeIndex(type); // maps command byte to an index (0 to NUM_TYPES-1)
                
                if (typeIndex != -1) {
                    memcpy(latestCmds[typeIndex], buffer, expectedCommandLength(type));
                    typeReceived[typeIndex] = true; // Mark that we've received a command of this type
                }
                
             } while (xQueueReceive(commandQueue, buffer, 0) == pdPASS); // Keep reading until the queue is empty to get the latest command of each type
             
             
             // Process the latest command of each type, if received
             
             for (int i = 0; i < NUM_TYPES; i++) {
                if (typeReceived[i]) {
                    handleCommand(latestCmds[i], expectedCommandLength(latestCmds[i][1]));
                }
             }
        }
    }
}