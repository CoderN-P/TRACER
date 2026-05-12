# Prints out sensor pckets every second from the esp32, to test the serial connection and packet parsing logic. Run this while the esp32 is sending packets, and you should see the sensor data printed out every second.
import logging
import time
import threading
from . import ROBOT_CONFIG
from .models import SerialManager, Robot, Command, CommandType, LCDCommand, MotorCommand

def serial_test(port=None):
    port = port if port else SerialManager.find_port()
    
    if not port:
        logging.error("No serial port found. Please connect the robot.")
        return


    last_print_time = 0
    
    print(f"Starting serial test on port {port}. You should see sensor data printed out every second if the connection and parsing are working correctly.")
    
    def callback(data):
        if not data: return
        
        # check if its been one second since the last print, and if so, print the sensor data
        nonlocal last_print_time
        if time.time() - last_print_time >= 1:
            print(Robot.bytes_to_sensor_data(data))
            
            last_print_time = time.time()
            
        
    serial_manager = SerialManager(port, 921600)
    serial_manager.start_read(callback=callback)
    
    serial_manager.send(Command(
        ID="",
        command_type=CommandType.LCD,
        command=LCDCommand(
            line_1="Serial Test",
            line_2="Running...",
        ),
        duration=0,
        pause_duration=0,
    ))

    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        print("Exiting serial test.")