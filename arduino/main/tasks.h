// tasks/tasks.h
#pragma once

void mainLoop(void* pvParameters);
void vSerialTask(void* pvParameters);
void commandProcessorTask(void* pvParameters);
void ultrasonicTask(void* pvParameters);
void oledUpdateTask(void* pvParameters);
void tofTask(void* pvParameters);
void sensorTransmitTask(void* pvParameters);