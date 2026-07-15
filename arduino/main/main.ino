#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include <WiFi.h>
#include "freertos/task.h"
#include <Wire.h>
#include "PID.h"
#include "config.h"
#include "sensors.h"
#include "motors.h"
#include "encoders.h"
#include "types.h"
#include "comms.h"
#include "tasks.h"
#include "OLED.h"
#include <atomic>

// RTOS task handles
TaskHandle_t ultrasonicTaskHandle;
TaskHandle_t mainLoopHandle;
TaskHandle_t serialTaskHandle;
TaskHandle_t sensorTransmitHandle;
TaskHandle_t commandProcessorHandle;
TaskHandle_t tofTaskHandle;
TaskHandle_t oledUpdateHandle;

static_assert(PID_INTERVAL == MAIN_INTERVAL, "PID and main loop intervals must match");

// PID Controllers
// Start with only feedforward for tuning
PIDController pidLeft;
PIDController pidRight;

RobotState robot_state;
SemaphoreHandle_t state_mutex;
SensorPacket packet;
GeneralConfig config;
SemaphoreHandle_t config_mutex;
SemaphoreHandle_t i2c_mutex;

QueueHandle_t commandQueue;
QueueHandle_t sensorQueue;
std::atomic<bool> motorsEnabled{true};
std::atomic<uint32_t> lastMotorCommandMs{0};

void setup()
{
    pinMode(IN1, OUTPUT);
    pinMode(IN2, OUTPUT);
    pinMode(IN3, OUTPUT);
    pinMode(IN4, OUTPUT);
    pinMode(TRIGGER_1, OUTPUT);
    pinMode(TRIGGER_2, OUTPUT);
    pinMode(ECHO_1, INPUT);
    pinMode(ECHO_2, INPUT);
    pinMode(STBY, OUTPUT);
    pinMode(BATTERY, INPUT);
    pinMode(ENCODER_LEFT_A, INPUT_PULLUP);
    pinMode(ENCODER_LEFT_B, INPUT_PULLUP);
    pinMode(ENCODER_RIGHT_A, INPUT_PULLUP);
    pinMode(ENCODER_RIGHT_B, INPUT_PULLUP);
    pinMode(ESTOP_PIN, INPUT_PULLUP);

    WiFi.mode(WIFI_OFF);

    attachInterrupt(digitalPinToInterrupt(ECHO_1), echoISR1, CHANGE);
    attachInterrupt(digitalPinToInterrupt(ECHO_2), echoISR2, CHANGE);
    attachInterrupt(digitalPinToInterrupt(ESTOP_PIN), estopISR, FALLING);

    setupEncoderLeft();

    setupEncoderRight();

    state_mutex = xSemaphoreCreateMutex();
    i2c_mutex = xSemaphoreCreateMutex();
    config_mutex = xSemaphoreCreateMutex();
    

    if (state_mutex == NULL || i2c_mutex == NULL)
    {
        while (true)
        {
            delay(1000);
        }
    }

    Wire.begin();
    Wire.setClock(400000); // Set I2C to 400kHz (Fast Mode)
    Wire.setTimeOut(20);   // Prevent indefinite stalls on a stuck I2C bus
    Serial.begin(BAUD_RATE);
    Serial.setTimeout(50);

    lastMotorCommandMs.store(millis());

    delay(1000); // Allow time for sensors to stabilize
    digitalWrite(STBY, HIGH);

    // Create the command queue (10 commands deep, each command can be up to MAX_BUFFER_SIZE bytes)
    commandQueue = xQueueCreate(10, sizeof(byte) * MAX_BUFFER_SIZE);
    sensorQueue = xQueueCreate(3, sizeof(SensorPacket));

    // setup_magnetometer(); // Not currently used
    setup_pwm();
    setupOLED();
    // setup_tof(); // Not currently used, so skip initialization to save time and I2C bandwidth
    
    if (setup_lsm6dos())
    {
        if (xSemaphoreTake(state_mutex, 0) == pdTRUE)
        {
            strncpy(robot_state.oledLine1, "Initialized", 16);
            strncpy(robot_state.oledLine2, "LSM6DOS OK", 16);
            xSemaphoreGive(state_mutex);
        }
    }
    else
    {
        // TODO: Display error on OLED
        if (xSemaphoreTake(state_mutex, 0) == pdTRUE)
        {
            strncpy(robot_state.oledLine1, "LSM6DOS Failed", 16);
            xSemaphoreGive(state_mutex);
        }
    }

    // Create RTOS tasks

    // Medium priority task for triggering ultrasonic sensors at 20 Hz
    // xTaskCreatePinnedToCore(ultrasonicTask, "Ultrasonic Task", 2048, NULL, 3, &ultrasonicTaskHandle, 0);

    // High priority task for sensor transmit loop (Sending sensor data)
    xTaskCreatePinnedToCore(sensorTransmitTask, "Sensor Transmit Task", 2048, NULL, 4, &sensorTransmitHandle, 0);
        
    // High priority task for main loop (PID, sensor reading) at 100 Hz,
    xTaskCreate(mainLoop, "Main Loop", 16384, NULL, 4, &mainLoopHandle);

    // Medium priority task for serial listening (below main loop to reduce control-loop jitter)
    xTaskCreatePinnedToCore(vSerialTask, "Serial Task", 2048, NULL, 3, &serialTaskHandle, 0);
    
    // Medium priority task for processing commands from the command queue
    xTaskCreatePinnedToCore(commandProcessorTask, "Command Processor Task", 4096, NULL, 3, &commandProcessorHandle, 0);

    // Medium priority task for reading time-of-flight sensor at 20 Hz (Not needed currently)
    // xTaskCreate(tofTask, "ToF Task", 2048, NULL, 3, &tofTaskHandle);

    // Low priority task for updating the OLED at 2 Hz
    xTaskCreate(oledUpdateTask, "OLED Update Task", 2048, NULL, 2, &oledUpdateHandle);
}

void loop()
{
    // Empty loop
}