#include "comms.h"
#include "config.h"
#include "motors.h"
#include "globals.h"

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
    if (cmd == CMD_TWIST)
        return 7;
    
    return 0; // invalid
}

uint8_t computeChecksum(uint8_t *data, uint8_t len)
{
    uint8_t sum = 0;
    for (uint8_t i = 0; i < len; i++)
    {
        sum += data[i];
    }
    return sum & 0xFF; // Return only the least significant byte
}

int getTypeIndex(uint8_t cmd)
{
    switch (cmd)
    {
    case CMD_MOVE:
        return 0;
    case CMD_OLED_UPDATE:
        return 1;
    case CMD_ENABLE:
        return 2;
    case CMD_STOP:
        return 3;
    case CMD_PWM:
        return 4;
    case CMD_CONFIG:
        return 5;
    case CMD_TWIST:
        return 6;
    default:
        return -1; // Invalid command type
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
    }
    else if (length != expectedCommandLength(cmd))
    {
        strncpy(line1, "Length Error", 16);
    }
    else if (cmd == CMD_MOVE && length == 7)
    {
        // Command 0x01: Handle movement
        int16_t leftVel, rightVel; // mm/s

        memcpy(&leftVel, &buffer[2], 2);
        memcpy(&rightVel, &buffer[4], 2);

        lastMotorCommandMs.store(millis());
        pendingPIDMode.store(0); // Switch to PID control mode

        pidLeft.setPendingSetpoint(leftVel / 1000.0f); // Convert mm/s to m/s for PID setpoint
        pidRight.setPendingSetpoint(rightVel / 1000.0f);
    }
    else if (cmd == CMD_OLED_UPDATE && length == 35)
    {
        // Command 0x02: Update OLED with two lines of text
        memcpy(line1, &buffer[2], 16);
        memcpy(line2, &buffer[18], 16);
    }
    else if (cmd == CMD_ENABLE && length == 3)
    {
        // Command 0x03: ENABLE
        lastMotorCommandMs.store(millis());

        digitalWrite(STBY, HIGH);

        motorsEnabled.store(true);
        pidLeft.reset();
        pidRight.reset();
        strncpy(line1, "Motors Enabled", 16);
    }
    else if (cmd == CMD_STOP && length == 3)
    {
        // Command 0x04: STOP
        lastMotorCommandMs.store(millis());
        motorsEnabled.store(false);
        digitalWrite(STBY, LOW);
        strncpy(line1, "Motors Stopped", 16);
    }
    else if (cmd == CMD_PWM && length == 7)
    {
        // Command 0x05: Direct PWM control (for testing)
        int16_t leftPWM_raw, rightPWM_raw; // 0 to 1000 for -1 to 1

        memcpy(&leftPWM_raw, &buffer[2], 2);
        memcpy(&rightPWM_raw, &buffer[4], 2);

        lastMotorCommandMs.store(millis());
        pendingPIDMode.store(1); // Switch to open-loop PWM control mode

        pidLeft.setPendingSetpoint(leftPWM_raw / 1000.0f);
        pidRight.setPendingSetpoint(rightPWM_raw / 1000.0f); // Convert to -1 to 1 range
        strncpy(line1, "Direct PWM Set", 16);
    } 
    else if (cmd == CMD_TWIST && length == 7){
        int16_t v_raw, omega_raw;
        
        memcpy(&v_raw, &buffer[2], 2);
        memcpy(&omega_raw, &buffer[4], 2);
        
        lastMotorCommandMs.store(millis());
        pendingPIDMode.store(2); // Switch to closed loop chassis control
        
        // quick cheat (store vlin in left pid setpoint and omega in right setpoint for main loop to process)
        pidLeft.setPendingSetpoint(v_raw / 1000.0f);
        pidRight.setPendingSetpoint(omega_raw / 1000.0f);
        
        strncpy(line1, "Twist mode", 16);
    }
    else if (cmd == CMD_CONFIG && length > 2 && length == buffer[2])
    {
        // Command 0x06: Update Config (Format = len,key,value...
        int i = 3;
        if (!(xSemaphoreTake(config_mutex, pdMS_TO_TICKS(5)) == pdTRUE)){
            strncpy(line1, "Config Busy", 16);
        } else {
            while (i < buffer[2]){
                // Key is uint8_t, so only 1 byte
                int rawKey;
                memcpy(&rawKey, &buffer[i++], 1);
                
                ConfigReg key = static_cast<ConfigReg>(rawKey);
                
                switch (key) {
                    case ConfigReg::PID_L_P:
                        int16_t pLeft;
                        memcpy(&pLeft, &buffer[i], 2); // PID constants are floats but sent as int16 to save space
                        config.pLeft = (float) pLeft / 1000.0;
                        i += 2;
                        break;
                    case ConfigReg::PID_L_I:
                        int16_t iLeft;
                        memcpy(&iLeft, &buffer[i], 2); // PID constants are floats but sent as int16 to save space
                        config.iLeft = (float) iLeft / 1000.0;
                        i += 2;
                        break;
                    case ConfigReg::PID_L_D:
                        int16_t dLeft;
                        memcpy(&dLeft, &buffer[i], 2); // PID constants are floats but sent as int16 to save space
                        config.dLeft = (float) dLeft / 1000.0;
                        i += 2;
                        break;
                    case ConfigReg::PID_R_P:
                        int16_t pRight;
                        memcpy(&pRight, &buffer[i], 2); // PID constants are floats but sent as int16 to save space
                        config.pRight = (float) pRight / 1000.0;
                        i += 2;
                    case ConfigReg::PID_R_I:
                        int16_t iRight;
                        memcpy(&iRight, &buffer[i], 2); // PID constants are floats but sent as int16 to save space
                        config.iRight = (float) iRight / 1000.0;
                        i += 2;
                        break;
                    case ConfigReg::PID_R_D:
                        int16_t dRight;
                        memcpy(&dRight, &buffer[i], 2); // PID constants are floats but sent as int16 to save space
                        config.dRight = (float) dRight / 1000.0;
                        i += 2;
                        break;
                    case ConfigReg::WHEEL_BASE_MAX:
                        uint16_t maxWheelBase;
                        memcpy(&maxWheelBase, &buffer[i], 2); 
                        config.maxWheelBase = (float) maxWheelBase / 1000.0;
                        i += 2;
                        break;
                    case ConfigReg::WHEEL_BASE_MIN:
                        uint16_t minWheelBase;
                        memcpy(&minWheelBase, &buffer[i], 2); 
                        config.minWheelBase = (float) minWheelBase / 1000.0;
                        i += 2;
                        break;
                    case ConfigReg::ALPHA:
                        int16_t alpha;
                        memcpy(&alpha, &buffer[i], 2);
                        config.alpha = (float) alpha / 1000.0;
                        i += 2;
                        break;
                    case ConfigReg::NOMINAL_WHEEL_BASE:
                        uint16_t nominalWheelBase;
                        memcpy(&nominalWheelBase, &buffer[i], 2); 
                        config.nominalWheelBase = (float) nominalWheelBase / 1000.0;
                        i += 2;
                        break;
                    case ConfigReg::LEFT_CORRECTION_POS:
                        int16_t leftCorrectionPos;
                        memcpy(&leftCorrectionPos, &buffer[i], 2);
                        config.leftCorrectionPos = (float) leftCorrectionPos / 1000.0;
                        i += 2;
                        break;
                    case ConfigReg::LEFT_CORRECTION_NEG:
                        int16_t leftCorrectionNeg;
                        memcpy(&leftCorrectionNeg, &buffer[i], 2);
                        config.leftCorrectionNeg = (float) leftCorrectionNeg / 1000.0;
                        i += 2;  
                        break;   
                    case ConfigReg::RIGHT_CORRECTION_POS:
                        int16_t rightCorrectionPos;
                        memcpy(&rightCorrectionPos, &buffer[i], 2);
                        config.rightCorrectionPos = (float) rightCorrectionPos / 1000.0;
                        i += 2;
                        break;
                    case ConfigReg::RIGHT_CORRECTION_NEG:
                        int16_t rightCorrectionNeg;
                        memcpy(&rightCorrectionNeg, &buffer[i], 2);
                        config.rightCorrectionNeg = (float) rightCorrectionNeg / 1000.0;
                        i += 2;
                        break;
                    case ConfigReg::I_ZONE:
                        uint16_t iZone;
                        memcpy(&iZone, &buffer[i], 2);
                        config.iZone = (float) iZone / 1000.0;
                        i += 2;
                        break;
                    case ConfigReg::USE_GYRO_CORRECTION:                                    
                        uint8_t useGyroCorrection;
                        memcpy(&useGyroCorrection, &buffer[i], 1);
                        config.useGyroCorrection = (bool) useGyroCorrection;
                        i += 1;
                        break;
                    case ConfigReg::USE_ADAPTIVE_WHEEL_BASE:
                        uint8_t useAdaptiveWheelBase;
                        memcpy(&useAdaptiveWheelBase, &buffer[i], 1);
                        config.useAdaptiveWheelBase = (bool) useAdaptiveWheelBase;
                        i += 1;
                        break;
                    case ConfigReg::OMEGA_P:
                        uint16_t omegaP;
                        memcpy(&omegaP, &buffer[i], 2);
                        config.omegaP = (float)  omegaP / 1000.0;
                        i += 2;
                        break;
                    case ConfigReg::MAX_LINEAR_VEL_POS:
                        uint16_t maxLinearVelPos;
                        memcpy(&maxLinearVelPos, &buffer[i], 2);
                        config.maxLinearVelPos = (float) maxLinearVelPos / 1000.0;
                        i += 2;
                        break;
                    case ConfigReg::MAX_LINEAR_VEL_NEG:
                        uint16_t maxLinearVelNeg;
                        memcpy(&maxLinearVelNeg, &buffer[i], 2);
                        config.maxLinearVelNeg = (float) maxLinearVelNeg / 1000.0;
                        i += 2;
                        break;      
                    default:
                        strncpy(line1, "Invalid cfg key", 16);
                }
            }
            xSemaphoreGive(config_mutex);
        }      
    }
    else
    {
        strncpy(line1, "Invalid Command", 16);
    }

    // Update OLED lines in robot state
    if (xSemaphoreTake(state_mutex, pdMS_TO_TICKS(0)) == pdTRUE)
    {
        strncpy(robot_state.oledLine1, line1, 16);
        strncpy(robot_state.oledLine2, line2, 16);
        xSemaphoreGive(state_mutex);
    }
}