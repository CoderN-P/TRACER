#include "sensors.h"
#include "motors.h"
#include "globals.h"
#include "Arduino.h"
#include "config.h"
#include "types.h"
#include "comms.h"
#include "driver/pcnt.h"

void mainLoop(void *pvParameters)
{
    const TickType_t xFrequency = pdMS_TO_TICKS(MAIN_INTERVAL);
    TickType_t xLastWakeTime = xTaskGetTickCount();

    uint8_t loopCounter = 0;
    uint8_t packetSeq = 0;
    int16_t prevPcntLeft = 0;
    int16_t prevPcntRight = 0;
    int32_t leftEncoderCount = 0;
    int32_t rightEncoderCount = 0;
    static portMUX_TYPE spinlock = portMUX_INITIALIZER_UNLOCKED;

    while (true)
    {
        vTaskDelayUntil(&xLastWakeTime, xFrequency);

        uint32_t loop_start = micros();

        if (!motorsEnabled)
        {
            handleMovement(0.0, 0.0); // Ensure motors are stopped if disabled
        }

        int16_t pcntLeft;
        int16_t pcntRight;
        int32_t echoDurationCopy1;
        int32_t echoDurationCopy2;
        int ax = 0, ay = 0, az = 0, gx = 0, gy = 0, gz = 0;
        float tempC = 0.0f;
        static float magX, magY, magZ; // Keep magnetometer data in static variables since it updates at 50 Hz

        pcnt_get_counter_value(pcnt_unit_left, &pcntLeft);
        pcnt_get_counter_value(pcnt_unit_right, &pcntRight);

        taskENTER_CRITICAL(&spinlock);
        {
            echoDurationCopy1 = echoDuration1;
            echoDurationCopy2 = echoDuration2;
        }
        taskEXIT_CRITICAL(&spinlock);

        int16_t deltaLeft = pcntLeft - prevPcntLeft;
        int16_t pcntRightCorrected = (-1 * pcntRight); // Invert right encoder count to match physical direction
        int16_t deltaRight = pcntRightCorrected - prevPcntRight;
        prevPcntLeft = pcntLeft;
        prevPcntRight = pcntRightCorrected;

        leftEncoderCount += deltaLeft;
        rightEncoderCount += deltaRight;

        getMPUData(ax, ay, az, gx, gy, gz, tempC);
        bool newMagData = loopCounter % 2 == 0; // Magnetometer updates at 50 Hz, so new data is available every 2 loops of the main loop

        if (newMagData)
        { // Read magnetometer at 50 Hz
            getMagnetometerData(magX, magY, magZ);
        }

        float leftSpeed, rightSpeed;
        float leftPWM, rightPWM;

        if (motorsEnabled)
        {
            leftSpeed = getLeftMotorSpeed(deltaLeft);
            rightSpeed = getRightMotorSpeed(deltaRight);
            auto [leftPWM_CPY, rightPWM_CPY] = pidLoop(leftSpeed, rightSpeed);
            leftPWM = leftPWM_CPY;
            rightPWM = rightPWM_CPY;
        }
        else
        {
            leftSpeed = 0;
            rightSpeed = 0;
            leftPWM = 0;
            rightPWM = 0;
        }

        float lastDistance1, lastDistance2;

        if (echoDurationCopy1 == 0 || echoDurationCopy1 > 25000)
        {
            lastDistance1 = -1;
        }
        else if (echoDurationCopy1 < 100)
        {
            lastDistance1 = -2;
        }
        else
        {
            lastDistance1 = (echoDurationCopy1 / 2.0) * 0.0343;
        }

        if (echoDurationCopy2 == 0 || echoDurationCopy2 > 25000)
        {
            lastDistance2 = -1;
        }
        else if (echoDurationCopy2 < 100)
        {
            lastDistance2 = -2;
        }
        else
        {
            lastDistance2 = (echoDurationCopy2 / 2.0) * 0.0343;
        }

        static uint8_t curBatteryPercent = 0;
        uint8_t irFront = getIRFront();
        uint8_t irBack = getIRBack();

        if (loopCounter % 10 == 0)
        { // Read battery voltage at 10 Hz
            curBatteryPercent = getBatteryPercent();
        }

        SensorPacket packet;

        packet.startByte = 0xAA;
        packet.packetSeq = packetSeq++;
        packet.distance_left = lastDistance1;
        packet.distance_right = lastDistance2;
        packet.distance_front = distanceFront;
        packet.ax = ax;
        packet.ay = ay;
        packet.az = az;
        packet.gx = gx;
        packet.gy = gy;
        packet.gz = gz;
        packet.tempC = tempC;
        packet.magX = magX;
        packet.magY = magY;
        packet.magZ = magZ;
        packet.leftEncoder = leftEncoderCount;
        packet.rightEncoder = rightEncoderCount;
        packet.flags = (irFront << 0) | (irBack << 1) | (newMagData << 2) | (motorsEnabled << 3); // Pack IR sensor states and new magnetometer data flag into flags byte
        packet.batteryPercent = curBatteryPercent;
        packet.timestamp = micros();
        packet.checksum = computeChecksum((uint8_t *)&packet, sizeof(packet) - 1);

        Serial.write((uint8_t *)&packet, sizeof(packet));

        int leftPIDMode = pidLeft.getMode();
        int rightPIDMode = pidRight.getMode();

        int mode;

        if (leftPIDMode == 1 && rightPIDMode == 1)
        {
            mode = 1; // Open-loop PWM control mode
        }
        else
        {
            mode = 0; // PID control mode
        }

        uint32_t loop_time = micros() - loop_start;
        float elapsed_ms = loop_time / 1000.0;

        if (xSemaphoreTake(state_mutex, 0) == pdTRUE)
        {
            robot_state.leftEncoder = leftEncoderCount;
            robot_state.rightEncoder = rightEncoderCount;
            robot_state.leftSpeed = leftSpeed;
            robot_state.rightSpeed = rightSpeed;
            robot_state.ax = ax;
            robot_state.ay = ay;
            robot_state.az = az;
            robot_state.gx = gx;
            robot_state.gy = gy;
            robot_state.gz = gz;
            robot_state.tempC = tempC;
            robot_state.magX = magX;
            robot_state.magY = magY;
            robot_state.magZ = magZ;
            robot_state.distance1 = lastDistance1;
            robot_state.distance2 = lastDistance2;
            robot_state.irFront = irFront;
            robot_state.irBack = irBack;
            robot_state.batteryPercent = curBatteryPercent;
            robot_state.mainLoopElapsedMs = elapsed_ms;
            robot_state.leftPWM = leftPWM;
            robot_state.rightPWM = rightPWM;
            robot_state.timestamp = packet.timestamp;
            robot_state.newMagData = newMagData;
            robot_state.pidMode = mode;
            robot_state.distanceFront = distanceFront;

            xSemaphoreGive(state_mutex);
        }

        loopCounter++;
    }
}