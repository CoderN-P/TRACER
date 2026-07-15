# Prints out sensor packets every second from the esp32, to test the serial connection and packet parsing logic. Run this while the esp32 is sending packets, and you should see the sensor data printed out every second.
import logging
import time
import threading
from . import ROBOT_CONFIG
from .models import SerialManager, SensorData, Robot, Command, CommandType, OLEDCommand, MotorCommand

def serial_test(port=None):
    port = port if port else SerialManager.find_port()
    
    if not port:
        logging.error("No serial port found. Please connect the robot.")
        return


    prev_sensor_data = None    
    print(f"Starting serial test on port {port}. You should see sensor data printed out every second if the connection and parsing are working correctly.")
    
    def callback(data):
        if not data: return
        
        # check if its been one second since the last print, and if so, print the sensor data
        nonlocal prev_sensor_data
        sensor_data = SensorData.from_bytes(data)
        if prev_sensor_data:
            print(sensor_data)            
        prev_sensor_data = sensor_data            
        
    serial_manager = SerialManager(port, 921600)
    serial_manager.start_read(callback=callback)
    
    serial_manager.send(Command(
        ID="",
        command_type=CommandType.OLED,
        command=OLEDCommand(
            line_1="Serial Test",
            line_2="Running...",
        ),
        duration=0,
        pause_duration=0,
    ))

    serial_manager.send(Command(
        ID="",
        command_type=CommandType.MOTOR,
        command=MotorCommand(
            left_motor=-0.3,
            right_motor=-0.3,
        ),
        duration=0,
        pause_duration=0,
    ))

    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        print("Exiting serial test.")
