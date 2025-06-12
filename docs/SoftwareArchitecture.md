# Software Architecture

![Software Architecture](/images/SoftwareArchitecture.png)

## Overview

The software architecture of the system is designed to be modular and scalable, allowing for easy integration of new features and components. The architecture consists of several key layers:

1. Arduino Hardware Layer
2. Raspberry Pi Layer
3. Web Interface Layer

## Arduino Hardware Layer

The Arduino hardware layer is responsible for interfacing with the physical components of the robot, including motors, sensors, and displays. It handles low-level operations such as reading sensor data, controlling motor speeds, and managing communication with the Raspberry Pi via USB serial.
Sensor data is collected at specific intervals and sent to the raspberry Pi via a request-response mechanism. The Arduino also listens for commands from the Raspberry Pi to control motors, displays, and other hardware components.

For serial communication information, refer to the [Serial Packets documentation](docs/SerialPackets.md).

### Key Components

- **Motors**: Controlled via PWM signals, allowing for speed and direction control. (2x JGB37 DC motors)
- **Sensors**: Includes ultrasonic distance sensors, IMU (Inertial Measurement Unit) for acceleration and gyroscope data, and IR sensors for cliff detection.
- **Display**: A 16x2 LCD display for showing status messages and sensor data.
- **Emergency Stop**: A mechanism to immediately stop all motors in case of an emergency, triggered by a specific command from the Raspberry Pi. (Disables STBY pin on the motor driver)
- **Serial Communication**: Uses USB serial for communication with the Raspberry Pi, sending sensor data and receiving commands.
- **TB6612FNG Motor Driver**: Controls the motors, allowing for speed and direction control via PWM signals.
- **Batteries**: Provides power to the motors and sensors (2x 18650 batteries in series for 7.4V, 2x 18650 batteries in parallel for 3.7V).

## Raspberry Pi Layer

The Raspberry Pi layer serves as the central processing unit of the system, handling higher-level logic, data processing, and communication with the web interface. It runs a Python application that processes incoming sensor data, makes decisions based on that data, and sends commands to the Arduino.
It hosts a FastAPI web server that uses websockets to listen for manual input from the web dashboard and also send sensor data to be displayed.

### Key Components
- **FastAPI Web Server**: Hosts the web interface and handles incoming requests from the web dashboard.
- **Serial Thread**: A dedicated thread for handling serial communication with the Arduino, ensuring that sensor data is read and commands are sent without blocking the main application.
- **Sensor Data Processing**: Processes incoming sensor data from the Arduino, including ultrasonic distance, IMU data, and IR sensor flags. Uses asyncio for non-blocking operations such as sending commands and emitting sensor data to the web interface.
- **WebSocket Communication**: Uses websockets to send real-time sensor data and receive manual control commands from the web interface.

## Web Interface Layer

The web interface layer provides a user-friendly dashboard for monitoring and controlling the robot. It allows users to view real-time sensor data, control motor speeds, and trigger emergency stops.

It has 2 parts, the web dashboard and the web backend. 

### Web Dashboard
- The web dashboard is built using SvelteKit with features such as 
  - Real-time sensor data display
  - Manual control of motors
  - Navigation controls (forward, backward, left, right)
  - Battery level indicator
  - AI natural language control (using OpenAI API)
  - Record and playback of commands/joystick macros

### Web Backend
- The web backend is built using Flask and serves the web dashboard. It handles requests from the web interface, processes them, and communicates with the Raspberry Pi via websockets.
- It also uses pygame to handle joystick rumbling and input events for manual control.

## Summary
The software architecture is designed to be modular, allowing for easy integration of new features and components. The Arduino hardware layer handles low-level operations, the Raspberry Pi layer processes data and manages communication, and the web interface layer provides a user-friendly dashboard for monitoring and control. This architecture enables efficient communication between the components and allows for real-time interaction with the robot.

