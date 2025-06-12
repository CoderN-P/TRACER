# TRACER

## Telemetry-driven Robot with Advanced Control and Execution Routines

## System Overview

TRACER is a modern, distributed robotics control system featuring a responsive web-based dashboard, intelligent command processing, and real-time controls. The architecture consists of three interconnected components:

1. **Frontend Dashboard** - Responsive SvelteKit web interface
2. **Raspberry Pi Controller** - Central processing and AI integration
3. **Arduino Hardware Interface** - Sensor management and motor control

The system is designed for mobile-friendly operation, intuitive controls, and expandability.
View [docs](/docs) for detailed architecture and hardware information.
view [demos](/docs/demos) for examples of the web dashboard and command processing.

## Key Features

- 🎮 **Multi-mode joystick control** - Supports arcade, tank, car, and single-joystick modes
- 📱 **Mobile-optimized dashboard** - Responsive design for all devices
- 🔄 **Joystick macro recording** - Record, save, and playback movement patterns
- 🧠 **AI-powered commands** - Natural language processing for robot control
- 📊 **Real-time telemetry** - Live sensor data visualization
- 🔋 **System monitoring** - Battery, temperature, and connectivity status
- 🛑 **Obstacle detection** - Proximity awareness with severity levels
- 💻 **Advanced logging** - Filterable, searchable system logs

## Project Structure

```
TRACER/
├── frontend/          # SvelteKit web dashboard
│   ├── src/           # Frontend source code
│   │   ├── lib/       # UI components and utilities
│   │   └── routes/    # Page routes
├── backend/           # Intermediary controller code
│   ├── Controller.py  # Joystick input processing
│   └── main.py        # Flask web server
├── rpi/               # Raspberry Pi robot controller
│   ├── src/           # Core robot functionality
│   │   ├── models/    # Robot models and types
│   │   ├── ai/        # GPT integration for commands
│   │   └── server.py  # WebSocket server
├── arduino/           # Arduino firmware
│   └── main/          # Main controller sketch
└── docs/              # Documentation
```

## Technical Architecture

### Frontend (Web Dashboard)

**Technology:** SvelteKit, TypeScript, Socket.IO, TailwindCSS

**Key Components:**

- Mobile-responsive control dashboard (`src/routes/+page.svelte`)
- Real-time joystick visualization with multiple control modes (`src/lib/components/JoystickStatus.svelte`)
- Command processing and display (`src/lib/components/CommandList.svelte`)
- Joystick macro recording and playback system (`src/lib/components/Recordings.svelte`) 
- Telemetry visualization including:
  - Obstacle detection (`src/lib/components/ObstructionStatus.svelte`)
  - Battery monitoring (`src/lib/components/BatteryPercentage.svelte`)
  - System status visualization (`src/lib/components/Status.svelte`)
  - Comprehensive logs (`src/lib/components/Logs.svelte`)

**Features:**

- Responsive design that works on mobile devices
- Real-time updates via WebSockets
- Joystick control with multiple driving modes:
  - Two-joystick arcade drive
  - Single-joystick arcade drive
  - Tank drive
  - Car drive (with trigger controls)
- Precision mode toggle for fine control
- Recording and playback of joystick macros
- Command history with visual status indicators
- Comprehensive logging with filtering
- Sensor data visualization

### Backend System

**Technology:** Python, Socket.IO, Flask, PyGame, WebSockets

**Components:**

1. **Controller Backend (Laptop/Server):**
   - `backend/main.py` - Flask server with Socket.IO
   - `backend/Controller.py` - Joystick handling and state management
   - `backend/ControllerState.py` - Control mode enumeration

2. **Robot Controller (Raspberry Pi):**
   - `rpi/src/server.py` - Main WebSocket server
   - `rpi/src/models/Robot.py` - Core robot functionality
   - `rpi/src/models/SerialManager.py` - Serial communication
   - `rpi/src/models/SensorData.py` - Sensor data processing
   - `rpi/src/ai/get_commands.py` - Natural language command integration

**Features:**

- Distributed architecture with dedicated controller and robot servers
- Physical controller support using PyGame 
- Multiple control modes (TWO_ARCADE, ONE_ARCADE, TANK, CAR)
- Precision mode toggle for fine control
- Macro recording and playback with named recordings
- Real-time WebSocket communication between components
- Natural language command processing with GPT integration
- Sensor data handling with safety features
- Cliff and obstacle detection with automatic responses
- Command queuing and execution with status feedback

### Arduino (Hardware Interface)

**Technology:** C++, Arduino Framework

**Key Components:**
- Main control loop (`arduino/main/main.ino`)
- Sensor interface modules
- Motor control system
- Serial communication handler

**Hardware Components:**
- TB6612FNG motor driver for differential drive
- MPU6050/9250 IMU (gyroscope + accelerometer)
- 1602 LCD with I2C backpack for local status display
- IR sensors for cliff detection
- HC-SR04 ultrasonic sensor for distance measurement

**Features:**
- Real-time sensor data collection and processing
- Motor control with hardware PWM
- Safety-first design with emergency stops
- Serialized data communication with the Raspberry Pi
- Local status display on LCD
- Battery voltage monitoring
- Obstacle and cliff detection

## Communication System

### Communication Flow
```
User Input (Web UI/Controller) → Backend Socket → Raspberry Pi → Serial → Arduino → Sensors
                                                                              ↓
Telemetry Display (Web UI) ← Backend Socket ← Raspberry Pi ← Serial Data ← Arduino
```

### Socket.IO Events

**Frontend ↔ Backend:**
- `joystick_input`: Send joystick control values to backend
- `joystick_mode`: Control mode changes (TWO_ARCADE, ONE_ARCADE, TANK, CAR)
- `precision_mode`: Toggle for precise movement control
- `start_recording`: Begin recording joystick movements
- `stop_recording`: End recording and save macro
- `play_recording`: Play back a saved joystick macro
- `sensor_data`: Streaming sensor updates from robot
- `active_command`: Current command being executed

**Backend ↔ Raspberry Pi:**
- `query`: Send natural language commands for AI processing
- `joystick_input`: Forward controller commands
- `sensor_data`: Telemetry updates
- `rumble`: Trigger controller haptic feedback
- `stop`: Emergency stop command

### Serial Protocol (Raspberry Pi ↔ Arduino)

**Command Structure:**
- Motor control: Binary packet with header and motor values
- LCD commands: Text display instructions
- Sensor requests: Periodic polling for data

**Response Structure:**
- Sensor data packets with ultrasonic, IMU, and IR readings
- Status acknowledgements
- Error messages

## Safety Features

- Emergency stop capability at all levels (UI, controller, code)
- Cliff detection with automatic stopping
- Obstacle avoidance with configurable thresholds
- Connection monitoring with auto-shutdown on disconnect
- Battery voltage monitoring and low-power warnings
- Watchdog timers for system stability

## Development and Deployment

**Requirements:**
- Python 3.10+ for backend and Raspberry Pi code
- Node.js and npm for frontend development
- Arduino IDE for firmware updates

**Running the System:**
1. Ensure all dependencies are installed:
   - For frontend: `npm install` in the `frontend` directory
   - For backend: Create venv and run `pip install -r requirements.txt` in the `backend` directory
   - For Raspberry Pi: Create venv and run `pip install -r requirements.txt` in the `rpi` directory
2. Upload `arduino/main/main.ino` to the Arduino board using the Arduino IDE
3. Run the raspberry Pi server:
   - Navigate to the `rpi` directory and run `python -m main`
4. Connect xbox controller to the laptop or server running the backend
   - Ensure the controller is recognized by the system (use `jstest` or similar tools to verify)
5. Start the backend server:
    - Navigate to the `backend` directory and run `python main.py`
6. Start the frontend server:
    - Navigate to the `frontend` directory and run `npm run dev`
    - Open the web dashboard in a browser at `http://localhost:5173`


## Future Enhancements

- Enhanced autonomous navigation capabilities
- Pure pursuit path following and PID control for smoother movement
- Motor encoders for precise localization
- Custom shield and mounts
- Camera integration for computer vision tasks
- Visual SLAM for mapping and localization
- Multi-robot coordination
- Additional sensor integration
- Machine learning for behavior optimization
- Mobile app control interface
