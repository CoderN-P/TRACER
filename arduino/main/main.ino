#include <WiFi.h>
#include <FreeRTOS/task.h>
#include <FreeRTOS/queue.h>
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


// RTOS task handles
TaskHandle_t ultrasonicTaskHandle;
TaskHandle_t mainLoopHandle;
TaskHandle_t serialTaskHandle;
TaskHandle_t commandProcessorHandle;
TaskHandle_t oledUpdateHandle;

static_assert(PID_INTERVAL == MAIN_INTERVAL, "PID and main loop intervals must match");

// PID Controllers
// Start with only feedforward for tuning
PIDController pidLeft(P_LEFT, I_LEFT, D_LEFT);
PIDController pidRight(P_RIGHT, I_RIGHT, D_RIGHT);

RobotState robot_state;
SemaphoreHandle_t state_mutex;
QueueHandle_t commandQueue;
volatile bool motorsEnabled = true;

void setup()
{
    pinMode(EN1, OUTPUT);
    pinMode(IN1, OUTPUT);
    pinMode(IN2, OUTPUT);
    pinMode(EN2, OUTPUT);
    pinMode(IN3, OUTPUT);
    pinMode(IN4, OUTPUT);
    pinMode(IR_FRONT, INPUT);
    pinMode(IR_BACK, INPUT);
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
    
    digitalWrite(STBY, HIGH);
    
    WiFi.mode(WIFI_OFF); 
    
    attachInterrupt(digitalPinToInterrupt(ECHO_1), echoISR1, CHANGE);
    attachInterrupt(digitalPinToInterrupt(ECHO_2), echoISR2, CHANGE);
    attachInterrupt(digitalPinToInterrupt(ESTOP_PIN), estopISR, FALLING);
    
    setupEncoderLeft();
    setupEncoderRight();

    state_mutex = xSemaphoreCreateMutex();
    Wire.begin();
    Wire.setClock(400000); // Set I2C to 400kHz (Fast Mode)
    Serial.begin(BAUD_RATE);
    Serial.setTimeout(50);

    delay(1000); // Allow time for sensors to stabilize
    digitalWrite(STBY, HIGH);
    
    // Create the command queue (10 commands deep, each command can be up to MAX_BUFFER_SIZE bytes)
    commandQueue = xQueueCreate(10, sizeof(byte) * MAX_BUFFER_SIZE);
    
    setup_magnetometer();
    setup_pwm();
    setupOLED();
    
    if (initMPU6050())
    {
        if (xSemaphoreTake(state_mutex, 0) == pdTRUE) {
            strncpy(robot_state.oledLine1, "System Initialized", 16);
            strncpy(robot_state.oledLine2, "MPU6050 OK", 16);
            xSemaphoreGive(state_mutex);
        }
    }
    else
    {
        // TODO: Display error on OLED
        if (xSemaphoreTake(state_mutex, 0) == pdTRUE) {
            strncpy(robot_state.oledLine1, "MPU6050 Init Failed", 16);
            xSemaphoreGive(state_mutex);
        }
    }
    
    // Create RTOS tasks
    
    // Medium priority task for triggering ultrasonic sensors at 20 Hz
    xTaskCreate(ultrasonicTask, "Ultrasonic Task", 2048, NULL, 3, &ultrasonicTaskHandle);
    
    // High priority task for main loop (PID, sensor reading, sending data) at 100 Hz, 
    xTaskCreate(mainLoop, "Main Loop", 4096, NULL, 4, &mainLoopHandle); 
    
    // High priority task for serial listening
    xTaskCreate(vSerialTask, "Serial Task", 2048, NULL, 4, &serialTaskHandle);
    // Medium priority task for processing commands from the command queue
    xTaskCreate(commandProcessorTask, "Command Processor Task", 4096, NULL, 3, &commandProcessorHandle);
    
    // Low priority task for updating the OLED at 2 Hz
    xTaskCreate(oledUpdateTask, "OLED Update Task", 2048, NULL, 2, &oledUpdateHandle);
}


void loop() {
    // Empty loop
}