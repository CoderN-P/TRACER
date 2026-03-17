#include "comms.h"
#include "config.h"
#include "motors.h"

uint8_t expectedCommandLength(uint8_t cmd)
{
    if (cmd == CMD_MOVE)
        return 7;
    if (cmd == CMD_OLED_UPDATE)
        return 35;
    if (cmd == CMD_STOP)
        return 3;
    if (cmd == CMD_ENABLE)
        return 3;
    if (cmd == CMD_PWM)
        return 7;
    return 0; // invalid
}

uint8_t computeChecksum(uint8_t* data, uint8_t len) {
    uint8_t sum = 0;
    for (uint8_t i = 0; i < len; i++) {
        sum += data[i];
    }
    return sum & 0xFF; // Return only the least significant byte
}

int getTypeIndex(uint8_t cmd) {
    switch (cmd) {
        case CMD_MOVE: return 0;
        case CMD_OLED_UPDATE: return 1;
        case CMD_ENABLE: return 2;
        case CMD_STOP: return 3;
        case CMD_PWM: return 4;
        default: return -1; // Invalid command type
    }
}

void handleCommand(byte *buffer, size_t length)
{
    uint8_t cmd = buffer[1]; // Command byte is the second byte (after start byte)
    uint8_t checksum = 0;
    
    char line1[17] = {0}; // 16 chars + null terminator
    char line2[17] = {0}; // 16 chars + null terminator
    
    for (size_t i = 0; i < length - 1; i++)
    {
        checksum += buffer[i];
    }
    if (checksum != buffer[length - 1])
    {
        strncpy(line1, "Checksum Error", 16);
        return;
    }
    if (cmd == CMD_MOVE && length == 7)
    {
        // Command 0x01: Handle movement
        int16_t leftVel, rightVel; // mm/s
        
        memcpy(&leftVel, &buffer[2], 2);
        memcpy(&rightVel, &buffer[4], 2);
        
        pidLeft.setSetpoint(leftVel / 1000.0f); // Convert mm/s to m/s for PID setpoint
        pidRight.setSetpoint(rightVel / 1000.0f);
    }
    else if (cmd == CMD_OLED_UPDATE && length == 35)
    {
        // Command 0x02: Update OLED with two lines of text
        memcpy(line1, &buffer[2], 16);
        memcpy(line2, &buffer[18], 16);
    } else if (cmd == CMD_ENABLE && length == 3){
        // Command 0x03: ENABLE
        motorsEnabled = true;
        digitalWrite(STBY, HIGH);
        pidLeft.reset();
        pidRight.reset();
        strncpy(line1, "Motors Enabled", 16);
         
    } else if (cmd == CMD_STOP && length == 3){
      // Command 0x04: STOP
        motorsEnabled = false;
        digitalWrite(STBY, LOW);
        strncpy(line1, "Motors Stopped", 16);
    } else if (cmd == CMD_PWM && length == 7){
        // Command 0x05: Direct PWM control (for testing)
        int16_t leftPWM_raw, rightPWM_raw; // 0 to 1000 for -1 to 1
        
        memcpy(&leftPWM_raw, &buffer[2], 2);
        memcpy(&rightPWM_raw, &buffer[4], 2);
        
        pidLeft.setPWMSetpoint(leftPWM_raw / 1000.0f);
        pidRight.setPWMSetpoint(rightPWM_raw / 1000.0f); // Convert to -1 to 1 range
        strncpy(line1, "Direct PWM Set", 16);
    }
    else
    {
        strncpy(line1, "Invalid Command", 16);
    }
    
    // Update OLED lines in robot state
    if (xSemaphoreTake(state_mutex, pdMS_TO_TICKS(5)) == pdTRUE) {
        strncpy(robot_state.oledLine1, line1, 16);
        strncpy(robot_state.oledLine2, line2, 16);
        xSemaphoreGive(state_mutex);
    }
}