# TRACER V2

## Telemetry-driven Robot with Advanced Control and Execution Routines

TRACER is a fully custom differential-drive robot built from scratch — hardware, firmware, and software. It features real-time autonomous path following, sensor fusion–based pose estimation, and a live web dashboard for monitoring and control. The system spans four interconnected layers: a SvelteKit web frontend, a Python relay backend, a Raspberry Pi robot controller, and an ESP32 firmware core.

View [docs](/docs) for detailed architecture and hardware information.
View [docs/demos](/docs/demos) for video and screenshot examples.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Web Dashboard                           │
│        SvelteKit + TypeScript + Socket.IO + Konva.js        │
└───────────────────────┬─────────────────────────────────────┘
                        │ Socket.IO (WebSocket)
┌───────────────────────▼─────────────────────────────────────┐
│                   Relay Backend (Laptop)                      │
│         Flask + Socket.IO + PyGame (controller input)        │
└───────────────────────┬─────────────────────────────────────┘
                        │ Socket.IO (WebSocket)
┌───────────────────────▼─────────────────────────────────────┐
│              Robot Controller (Raspberry Pi)                  │
│   FastAPI + asyncio + state estimation + path following      │
└───────────────────────┬─────────────────────────────────────┘
                        │ UART Serial (115200 baud)
┌───────────────────────▼─────────────────────────────────────┐
│                  Firmware (ESP32 / Arduino)                   │
│       FreeRTOS + PID motor control + sensor acquisition      │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Features

### Autonomous Navigation
- 🛤️ **Quintic Hermite spline paths** — C2-continuous trajectories designed interactively in the web dashboard; parameterized by position, velocity, and acceleration at each endpoint
- 🏎️ **RAMSETE tracking controller** — nonlinear feedback controller for accurate spline path following with time-parameterized trajectory interpolation
- 🎯 **Pure Pursuit controller** — lookahead-based path following for freehand-drawn waypoint paths
- ⚡ **Velocity profiling** — curvature-constrained speed profiles generated per spline segment in a background process

### State Estimation
- 📐 **Differential drive odometry** — dead-reckoning from quadrature encoder ticks at 100 Hz
- 🧭 **Kalman filter heading estimation** — fuses gyroscope (MPU6050) and magnetometer (QMC5883L) using a two-stage EKF: encoder-derived heading as primary measurement, magnetometer as secondary correction
- 🗺️ **Full pose tracking** — x, y position (meters) + yaw (radians) + linear/angular velocity, streamed to the dashboard at 10 Hz

### Web Dashboard
- 🗺️ **Interactive path editor** — pan/zoom canvas with quintic Hermite spline editing (drag control points for position, velocity, and acceleration handles) and freehand drawing mode (1 cm point spacing)
- 🤖 **Live robot overlay** — robot pose rendered on the path canvas with heading arrow and lerp-smoothed 10 Hz position updates
- 🟢 **Run mode** — send a spline or freehand path to the robot with one click; path is visually offset to start at the robot's current position; run mode exits automatically on `path_complete` confirmation
- 🛑 **Emergency stop & manual override** — dedicated E-Stop and Manual mode buttons always visible in the status bar
- 📊 **Real-time telemetry** — ultrasonic distance graph, battery %, IMU temperature, sensor packet rate
- 🎮 **Joystick control** — physical Xbox controller support (arcade/tank/car modes, precision mode, rumble feedback) plus on-screen virtual joystick
- 🔴 **Macro recording** — record, name, save, and replay joystick movement sequences
- 🧠 **AI commands** — natural language input processed via GPT into structured motor/LCD command sequences

### Firmware (ESP32 + FreeRTOS)
- ⚙️ **Velocity PID + feedforward** — separate PID controllers for left and right wheels with kS + kV feedforward; hardware pulse-count peripheral (PCNT) for encoder counting
- 📡 **100 Hz main loop** — RTOS tasks for motor control, serial I/O, ultrasonic sensing, OLED display, and command processing all running concurrently
- 🔌 **Hardware interrupt E-Stop** — dedicated pin with falling-edge ISR for immediate motor cutoff
- 📦 **Binary serial protocol** — compact 37-byte sensor packets (start byte, sequence number, distance, IMU 6-axis, temperature, magnetometer 3-axis, encoder ticks, IR flags, battery %, timestamp, checksum)

---

## Project Structure

```
TRACER/
├── frontend/                  # SvelteKit web dashboard
│   └── src/
│       ├── lib/
│       │   ├── components/    # UI components
│       │   │   ├── PathDrawer.svelte          # Path editor + robot overlay
│       │   │   ├── RobotControls.svelte       # E-Stop + Manual mode buttons
│       │   │   ├── UltrasonicGraph.svelte     # Distance history chart
│       │   │   ├── ControlPad.svelte          # On-screen joystick
│       │   │   └── ...
│       │   ├── types/         # Zod schemas + Svelte rune classes
│       │   │   ├── QuinticHermiteSpline.svelte.ts
│       │   │   ├── SplinePath.svelte.ts
│       │   │   └── ...
│       │   └── api/
│       │       └── socket.ts  # Socket.IO client singleton
│       └── routes/
│           └── +page.svelte   # Main dashboard page
│
├── backend/                   # Relay server (runs on laptop/server)
│   ├── main.py                # Flask + Socket.IO relay + joystick input
│   ├── Controller.py          # Xbox controller handling via PyGame
│   └── GestureController.py   # ESP32 IMU gesture sensor integration
│
├── rpi/                       # Raspberry Pi robot controller
│   └── src/
│       ├── server.py          # FastAPI + asyncio Socket.IO server
│       └── models/
│           ├── Robot.py               # Main robot class + state machine
│           ├── StateEstimator.py      # Odometry + velocity estimation
│           ├── HeadingFilter.py       # EKF heading filter (gyro + mag)
│           ├── PoseFilter.py          # EKF position filter (encoder dead-reckoning)
│           ├── QuinticHermiteSpline.py # Spline math + arc length LUT + velocity profile
│           ├── Path.py                # Multi-segment path + trajectory builder (subprocess)
│           ├── RAMSETE.py             # RAMSETE trajectory tracking controller
│           ├── PurePursuit.py         # Pure pursuit controller for freehand paths
│           ├── SerialManager.py       # UART serial communication with ESP32
│           ├── SensorData.py          # Pydantic sensor data model
│           ├── RobotState.py          # Pydantic robot state model (pose + velocity)
│           ├── Config.py              # All physical robot constants
│           └── Mode.py                # State machine modes
│
├── arduino/                   # ESP32 firmware
│   └── main/
│       ├── main.ino           # RTOS task creation + hardware init
│       ├── mainLoop.cpp       # 100 Hz loop: sensors, PID, serial TX
│       ├── serialTask.cpp     # Serial RX + command queue
│       ├── commandProcessorTask.cpp  # Motor + LCD command execution
│       ├── motors.cpp         # PWM motor driver (TB6612FNG)
│       ├── sensors.cpp        # IMU + magnetometer reading
│       ├── encoders.cpp       # Hardware PCNT encoder interface
│       ├── ultrasonicTask.cpp # 20 Hz ultrasonic trigger/read
│       ├── PID.cpp / PID.h    # PID controller implementation
│       └── config.h           # Pin assignments + tuning constants
│
└── docs/                      # Architecture and protocol documentation
```

---

## Socket.IO Event Reference

### Frontend ↔ Backend (Relay)

| Event | Direction | Payload | Description |
|---|---|---|---|
| `joystick_input` | → | `{ left_y, right_x }` | Drive command from UI or controller |
| `set_state` | → | `{ state, path_type?, path? }` | Change robot mode; include path for `PATH_FOLLOWING` |
| `query` | → | `{ query }` | Natural language command string |
| `start_recording` | → | — | Begin recording joystick macro |
| `stop_recording` | → | — | Stop and save macro |
| `play_recording` | → | `{ timestamp }` | Replay a saved macro |
| `precision_mode` | → | — | Toggle precision drive mode |
| `stop` | → | — | Emergency stop |
| `sensor_data` | ← | sensor + state + mode | 10 Hz telemetry from robot |
| `path_complete` | ← | `{ status }` | Robot finished executing path |
| `active_command` | ← | command object | Current AI command being executed |
| `obstacle_detected` | ← | `{ distance }` | Ultrasonic obstacle alert |
| `cliff_detected` | ← | `{ ir_front, ir_back }` | IR cliff detection alert |

### `set_state` Payload — `PATH_FOLLOWING`

**Freehand (Pure Pursuit):**
```json
{
  "state": "PATH_FOLLOWING",
  "path_type": "freehand",
  "path": [{ "x": 0.0, "y": 0.0 }, ...]
}
```

**Spline (RAMSETE):**
```json
{
  "state": "PATH_FOLLOWING",
  "path_type": "spline",
  "path": {
    "splines": [{
      "start": [x0, y0],
      "end": [x1, y1],
      "start_velocity": [dx0, dy0],
      "end_velocity": [dx1, dy1],
      "start_acceleration": [ddx0, ddy0],
      "end_acceleration": [ddx1, ddy1]
    }]
  }
}
```

### Serial Protocol (Raspberry Pi ↔ ESP32)

**Sensor packet (ESP32 → RPi), 37 bytes, 100 Hz:**
```
<B  start byte (0xAA)
 B  packet sequence number
 f  ultrasonic distance (cm, -1=too far, -2=too close)
 hhhhhh  IMU: ax, ay, az, gx, gy, gz (raw int16)
 f  temperature (°C)
 fff  magnetometer x, y, z (µT)
 ii  left/right encoder ticks (int32, delta per loop)
 B  flags: bit0=IR front, bit1=IR back, bit2=new mag data
 B  battery percentage
 I  timestamp (µs, uint32)
 B  checksum (sum of all bytes mod 256)>
```

**Command packet (RPi → ESP32):**
- Motor command: left + right wheel velocity targets (m/s), scaled to PWM
- LCD command: two 16-char text lines for I2C display

---

## Hardware

| Component | Part |
|---|---|
| Microcontroller | ESP32 (Arduino framework) |
| Motor driver | TB6612FNG (dual H-bridge) |
| Motors | JGB37-520 gear motors with quadrature encoders (56:1, 178 RPM max) |
| IMU | MPU6050 (6-axis accel/gyro, I2C) |
| Magnetometer | QMC5883L (3-axis, I2C) |
| Distance sensor | HC-SR04 ultrasonic (dual, interrupt-driven) |
| Display | SSD1306 128×64 OLED (I2C) |
| Cliff detection | IR sensors (front + rear) |
| Battery monitor | Voltage divider on ADC pin |
| Main computer | Raspberry Pi (runs path following + state estimation) |
| E-Stop | Hardware interrupt pin (falling edge ISR) |

---

## Running the System

### Prerequisites
- Python 3.10+ (backend and RPi)
- Node.js 18+ (frontend)
- Arduino IDE or PlatformIO (firmware)
- Xbox controller (optional, for physical joystick input)

### 1 — Firmware
Upload `arduino/main/main.ino` to the ESP32 via Arduino IDE.

### 2 — Raspberry Pi
```bash
cd rpi
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m main
```

### 3 — Relay Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
```
Connect an Xbox controller before starting if physical joystick input is needed.

### 4 — Web Dashboard
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in a browser.

---

## Calibration

Several constants in `rpi/src/models/Config.py` and `arduino/main/config.h` require physical calibration:

| Constant | Tool | Description |
|---|---|---|
| `WHEEL_BASE_CORRECTION` | `rpi/src/calibrate_wheelbase.py` | Correct odometry heading for actual track width |
| `LEFT/RIGHT_CORRECTION` | `rpi/src/calibrate_wheel.py` | Correct per-wheel distance from encoder ticks |
| `kS_LEFT/RIGHT` | `rpi/src/calibrate_kS.py` | Static friction feedforward for each motor |
| Magnetometer offsets | `backend/mag_calibration.py` | Hard/soft iron calibration via ellipsoid fitting |
| PID gains | `arduino/main/config.h` | `P_LEFT`, `I_LEFT`, `D_LEFT` (and right equivalents) |


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
- Custom shield and mounts
- Camera integration for computer vision tasks
- Visual SLAM for mapping and localization
- Multi-robot coordination
- Additional sensor integration
- Machine learning for behavior optimization
- Mobile app control interface
