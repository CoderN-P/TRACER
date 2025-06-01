import time
import pygame
import serial
import time
import json
from models import Command, MotorCommand

baud = 9600

def initialize_serial(port: str):
    """
    Initialize the serial connection to the robot.
    """
    try:
        ser = serial.Serial(port, baudrate=baud, timeout=1)
        time.sleep(2)  # Wait for the serial connection to initialize
        return ser
    except serial.SerialException as e:
        raise RuntimeError(f"Failed to connect to the robot on port {port}: {e}")

def initialize_controller():
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        raise RuntimeError("No controllers found")

    controller = pygame.joystick.Joystick(0)
    controller.init()
    
    return controller

def read_controller_input(controller) -> tuple:
    left_y = controller.get_axis(1)
    right_x = controller.get_axis(2)

    return left_y, right_x

def calculate_diff_drive(controller) -> tuple:
    """
    Calculate the differential drive values based on the controller input.
    """
    left_y, right_x = read_controller_input(controller)
    left_motor  = -left_y * 255 * (1 - right_x)
    right_motor = -left_y * 255 * (1 + right_x)
    
    return left_motor, right_motor

def send_command(command: Command, ser: serial.Serial) -> None:
    """
    Send a command to the robot via serial.
    """
    command_json = command.model_dump_json()
    
    try:
        ser.write(command_json.encode('utf-8') + b'\n')
        ser.flush()
        print("sent")
    except serial.SerialException as e:
        raise RuntimeError(f"Failed to send command: {e}")
    
def get_motor_command(left_motor: float, right_motor: float) -> Command:
    """
    Create a motor command based on the left and right motor values.
    """
    return Command(
        ID="",
        command_type="MOTOR",
        command=MotorCommand(
            left_motor=int(left_motor),
            right_motor=int(right_motor)
        ),
        pause_duration=0,
        duration=0
    )
    
def get_data_from_serial(ser: serial.Serial):
    """
    Read data from the serial port.
    """
    try:
        print(ser.in_waiting)
        if ser.in_waiting > 0:
            data = ser.readline().decode('utf-8').strip()
            return data
        return None
    except serial.SerialException as e:
        raise RuntimeError(f"Failed to read from serial: {e}")
    
    
def controller_moved(controller) -> bool:
    """
    Check if the controller has moved.
    """
    left_y = controller.get_axis(1)
    right_x = controller.get_axis(2)
    
    if abs(left_y) > 0.5 or abs(right_x) > 0.5:
        return True
    return False
    

def main():
    port = '/dev/cu.DSDTECHHC-05'  # Change this to your serial port
    ser = initialize_serial(port)
    ser.write(
        b'whats up?\n'  # Initial command to check connection
    )
    print("Serial connection established. Waiting for response...")
    clock = pygame.time.Clock()
    controller = initialize_controller()

    try:
        while True:
            data = get_data_from_serial(ser)
            if data:
                print(data)
            pygame.event.pump()
            
            if (not controller_moved(controller)):
                clock.tick(60)
                continue
            
            left_motor, right_motor = calculate_diff_drive(controller)
            command = get_motor_command(left_motor, right_motor)
            send_command(command, ser)
            
            

            clock.tick(60)

    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        ser.close()
        pygame.quit()
    
    
if __name__ == "__main__":
    main()
    



