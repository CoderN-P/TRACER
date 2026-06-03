#include "globals.h"
#include "types.h"
#include "Arduino.h"

void sensorTransmitTask(void *pvParameters){
    while (true) {
        SensorPacket localPacket;
        if (xQueueReceive(sensorQueue, &localPacket, portMAX_DELAY) == pdTRUE) {
            Serial.write((uint8_t*)&localPacket, sizeof(SensorPacket));
        }
    }
}
