#include "globals.h"
#include "types.h"
#include "Arduino.h"

void sensorTransmitTask(void *pvParameters){
    while (true) {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
        xSemaphoreTake(sensor_mutex, portMAX_DELAY);
        SensorPacket localPacket;
        memcpy(&localPacket, &packet, sizeof(SensorPacket));
        xSemaphoreGive(sensor_mutex);
        Serial.write((uint8_t*)&localPacket, sizeof(SensorPacket));
    }
}
