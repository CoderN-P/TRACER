# TRACER V2

**Telemetry-driven Robot with Advanced Control and Execution Routines**

![TRACER robot hero](/images/RobotHero.png)

TRACER is a custom differential-drive robot built across the whole stack: browser dashboard, Python relay, Raspberry Pi robot brain, and ESP32 firmware. You can drive it manually, draw and follow paths from a web UI, estimate its pose from live sensors, and stream telemetry back while it runs.

The short version: **draw a route in the browser, send it to the robot, watch the pose and sensors update live, and stop everything instantly if something goes wrong.**

## What It Does

![Live dashboard](/images/Dashboard.png)

- **Autonomous path following:** quintic Hermite spline paths, curvature-aware velocity profiling, RAMSETE tracking, and Pure Pursuit for freehand routes.
- **Live pose estimation:** wheel encoder odometry fused with gyro and magnetometer heading, plus a pose filter ready for lidar/camera corrections.
- **Real-time control loop:** web commands and joystick input flow through Socket.IO to the Pi, then to the ESP32 over 921600-baud serial.
- **Natural-language commands:** optional GPT-powered command parsing turns plain English into structured robot actions.
- **Safety-first driving:** emergency stop, motor command timeout, obstacle state handling, battery telemetry, and sensor health visibility.

## How It Works

![Software architecture](/images/SoftwareArchitecture.png)

TRACER is split into four layers so each part does the job it is best at:

| Layer | Runs On | Job |
| --- | --- | --- |
| Web dashboard | Browser | Path editing, telemetry visualization, manual controls, command UI |
| Relay backend | Laptop/server | Socket.IO bridge, Xbox controller input, rumble feedback |
| Robot controller | Raspberry Pi | Async robot loop, state estimation, path following, obstacle handling |
| Firmware | ESP32 / Arduino | Motor PID/feedforward, encoders, IMU, ToF/ultrasonic sensors, OLED/status |

Telemetry moves back up the same chain, so the dashboard can show what the robot thinks is happening while the robot is actually moving.

## Cool Features

### Browser-Drawn Trajectories

![Path editor](/images/PathEditor.png)

The dashboard is not just a remote control. It is a path editor with pan/zoom, grid coordinates, draggable spline handles, live robot overlay, route stats, and run/stop controls. Spline paths are exported as structured trajectories; freehand paths can be followed with Pure Pursuit.

### State estimation + Sensor fusion

![Pose estimation](/images/PoseEstimation.png)

The Raspberry Pi keeps a live robot state: `x`, `y`, yaw, linear velocity, and angular velocity. Encoder deltas provide motion, the gyro handles fast heading changes, the magnetometer corrects drift, and filter snapshots allow delayed lidar/camera measurements to be replayed into the pose estimate.

### High-Speed Firmware Link

![Serial telemetry](/images/SerialTelemetry.png)

The ESP32 streams compact 37-byte sensor packets to the Pi with a start byte, packet number, wheel encoder deltas, ultrasonic/ToF distances, IMU, magnetometer, flags, battery, timestamp, and checksum. Motor commands go the other way as binary packets, keeping the robot loop fast and predictable.

## Repo Map

```text
frontend/   SvelteKit dashboard, path editor, telemetry UI
backend/    Flask + Socket.IO relay and controller input
rpi/        FastAPI/asyncio robot brain, estimation, path following
arduino/    ESP32 firmware, motor control, sensor packets
docs/       Deeper architecture notes and demos
images/     README visuals and future screenshots
```

## Quick Start

Install and run each layer in its own terminal.

```bash
cd frontend
npm install
npm run dev
```

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

```bash
cd rpi
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Upload the firmware from `arduino/main` to the ESP32/Arduino board, then open the dashboard at `http://localhost:5173`.

## Deep Dives

- [Software architecture](/docs/SoftwareArchitecture.md)
- [Hardware architecture](/docs/HardwareArchitecture.md)
- [Serial packets](/docs/SerialPackets.md)
- [Dashboard demos](/docs/demos/WebDashboard.md)
- [AI control demo](/docs/demos/AIControl.md)
