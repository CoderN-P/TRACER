# TRACER - Final Architecture
## Telemetry-driven Robot with AI-powered Control and Execution Routines

## System Overview
TRACER is a distributed control system with three main components: Laptop (UI/Controller), Raspberry Pi 3B+ (Brain), and Arduino (Hardware Interface). Each component handles specific responsibilities optimized for its capabilities.

## Component Breakdown

### Laptop (User Interface & Controller)
**Role:** Human interface and high-level command input
**Hardware:** Standard laptop with game controller connected
**Software:** 
- SvelteKit dashboard application
- Simple socket client for Pi communication
- Controller input handler
- Image processing modules (OpenCV/ML models)

**Responsibilities:**
- Serve interactive web dashboard for robot control
- Capture and process game controller inputs
- Handle camera feed processing (computer vision tasks)
- Send high-level commands to Raspberry Pi
- Display real-time robot status and sensor data
- Provide haptic feedback through controller rumble

**Communication:**
- Socket connection to Raspberry Pi
- Sends: Controller commands, path waypoints, text commands, processed vision data
- Receives: Status updates, sensor data, feedback commands (rumble intensity)

### Raspberry Pi 3B+ (Robot Brain)
**Role:** Central processing unit and decision-making hub
**Hardware:** Raspberry Pi 3B+ with camera module
**Software:**
- Python Flask backend with SocketIO
- Pure pursuit path planning algorithm
- Kalman filter for sensor fusion
- GPT API integration for natural language processing
- Serial communication handler

**Responsibilities:**
- Process controller inputs into robot movement commands
- Execute autonomous path following using pure pursuit algorithm
- Perform sensor fusion with Kalman filtering (IMU + odometry data)
- Convert natural language commands to actionable robot instructions via GPT API
- Manage real-time communication between laptop and Arduino
- Capture and stream camera feed to laptop for processing
- Handle safety logic and emergency stops

**Communication:**
- Socket server for laptop connection
- Serial USB connection to Arduino
- Camera data streaming to laptop

**Data Processing:**
- Raw sensor data → Kalman filter → State estimation
- Controller inputs → Motion planning → Motor commands
- Text commands → GPT API → JSON command structure
- Vision data from laptop → Navigation decisions

### Arduino (Hardware Interface)
**Role:** Real-time hardware control and sensor management
**Hardware:** Arduino board with sensor/actuator shield
**Software:** C++ firmware with main control loop
**Connected Components:**
- TB6612FNG motor driver for differential drive
- MPU6050/9250 IMU (gyroscope + accelerometer)
- 1602 LCD with I2C backpack for local status display
- IR sensor for obstacle detection
- HC-SR04 ultrasonic sensor for distance measurement

**Responsibilities:**
- Execute precise motor control with hardware PWM
- Read sensor data at high frequency (100Hz+ for IMU)
- Provide real-time safety responses (emergency stops)
- Send periodic sensor data packets to Raspberry Pi
- Display basic status information on LCD
- Handle low-level hardware interfacing

**Communication:**
- Serial USB connection to Raspberry Pi
- Receives: Motor commands, LED commands, display updates
- Sends: Sensor data JSON packets, status updates, error messages

## Data Flow Architecture

### Primary Control Loop
```
User Input (Laptop) → Socket → Pi Processing → Serial → Arduino Execution → Sensors → Serial → Pi State Update → Socket → Laptop Display
```

### Autonomous Navigation Flow
```
Pi Path Planning → Motor Commands → Arduino → Sensors → Pi Kalman Filter → State Estimate → Path Planning (loop)
```

### Vision Processing Pipeline
```
Pi Camera → Laptop Processing → Object Detection/Navigation Data → Pi Decision Making → Arduino Commands
```

## Communication Protocols

### Laptop ↔ Raspberry Pi (Socket)
**Command Structure:**
```json
{
  "type": "controller_input",
  "data": {"x": 0.5, "y": 0.8, "buttons": ["A"]}
}

{
  "type": "path_command", 
  "data": {"waypoints": [[1.0, 2.0], [3.0, 4.0]]}
}

{
  "type": "text_command",
  "data": {"command": "move forward 2 meters and turn left"}
}
```

**Response Structure:**
```json
{
  "type": "status_update",
  "data": {"position": [1.2, 3.4], "battery": 85, "state": "moving"}
}

{
  "type": "controller_feedback",
  "data": {"rumble": 0.3, "duration": 500}
}
```

### Raspberry Pi ↔ Arduino (Serial)
**Command Format:**
```json
{"cmd": "motor", "left": 150, "right": 100}
{"cmd": "led", "state": "on", "color": "blue"}
{"cmd": "display", "line1": "Status: OK", "line2": "Dist: 45cm"}
```

**Sensor Data Format:**
```json
{
  "timestamp": 1234567890,
  "imu": {"ax": 0.1, "ay": 0.2, "az": 9.8, "gx": 0.01, "gy": 0.02, "gz": 0.03},
  "ultrasonic": {"distance": 45.2},
  "ir": {"detected": false},
  "motors": {"left_speed": 150, "right_speed": 100}
}
```

## Software Architecture Details

### Raspberry Pi Python Backend
**Key Modules:**
- `main.py` - Flask app with SocketIO server
- `robot_controller.py` - Pure pursuit and motion planning
- `sensor_fusion.py` - Kalman filter implementation  
- `gpt_interface.py` - Natural language command processing
- `arduino_comm.py` - Serial communication handler
- `safety_monitor.py` - Emergency stop and safety logic

**Key Classes:**
- `RobotState` - Current position, velocity, orientation
- `PathPlanner` - Pure pursuit algorithm implementation
- `KalmanFilter` - Sensor fusion for state estimation
- `CommandProcessor` - GPT API integration

### Arduino Firmware Structure
**Core Functions:**
- `setup()` - Initialize sensors, motors, communications
- `loop()` - Main control loop (sensor reading, command execution)
- `readSensors()` - High-frequency sensor data collection
- `executeCommand()` - Parse and execute Pi commands
- `sendSensorData()` - Periodic data transmission to Pi
- `emergencyStop()` - Safety shutdown procedures

**Timing Requirements:**
- Main loop: 50Hz (20ms cycle time)
- IMU reading: 100Hz
- Sensor data transmission: 20Hz
- Motor command execution: Real-time response

## Performance Considerations

### Raspberry Pi 3B+ Optimization
- Single Python backend process to minimize memory usage
- Efficient sensor data buffering and processing
- Asynchronous socket handling for responsive communication
- Camera resolution optimization for network bandwidth
- Kalman filter optimization for real-time performance

### Network Communication
- JSON message compression for large data packets
- Heartbeat monitoring for connection reliability
- Command queuing with priority handling
- Error recovery and reconnection logic

### Arduino Optimization
- Hardware interrupts for critical timing
- Efficient serial buffer management
- Non-blocking sensor reading routines
- Watchdog timer for safety monitoring

## Safety Features
- Emergency stop capability at all levels
- Watchdog timers on Arduino for fault detection
- Connection monitoring between all components
- Safe motor shutdown on communication loss
- Battery voltage monitoring and low-power warnings
- Obstacle detection with automatic stopping

## Development and Testing Strategy
- Modular development allowing independent testing of each component
- Serial monitor debugging for Arduino communication
- Socket message logging for Pi-Laptop communication  
- Unit tests for critical algorithms (Kalman filter, pure pursuit)
- Hardware-in-the-loop testing capabilities
- Simulation mode for algorithm development without hardware

## Future Expansion Capabilities
- Additional sensor integration through Arduino digital/analog pins
- Computer vision algorithm upgrades on laptop
- Advanced path planning algorithms on Pi
- Multi-robot coordination through laptop orchestration
- Machine learning model deployment for behavior learning
- Mobile app interface through laptop web server proxy
