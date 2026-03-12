#ifndef COMMS_H
#define COMMS_H

#include "config.h"
#include "globals.h"
#include <Arduino.h>

uint8_t expectedCommandLength(uint8_t cmd);
uint8_t computeChecksum(uint8_t* data, uint8_t len);
int getTypeIndex(uint8_t cmd);
void handleCommand(byte *buffer, size_t length);

#endif