# TRACER
# **Telemetry-driven Robot with AI-powered Control and Execution Routines

## **Overview**
This project is an experimental robotics system that combines low-level embedded systems programming with high-level AI-driven control. It features a robot built on an Arduino microcontroller, enhanced by a laptop-side software stack that uses natural language processing, real-time decision-making, and a web-based interface for monitoring and control.

---

## **Objective**
To create a robotics system capable of interpreting natural language commands using a local LLM and executing them via an Arduino-controlled vehicle. The system supports manual and autonomous navigation modes, and future extensions include vision processing and obstacle detection.

---

## **System Architecture**

### **Hardware Components**
- **Arduino Uno/Nano** — microcontroller for sensor reading and motor control.
- **Bluetooth Module (e.g., HC-05)** — communication between Arduino and laptop.
- **Gear Motors + Motor Driver (e.g., L298N)** — for movement.
- **Wheel Encoders** — for position tracking.
- **IR & Ultrasonic Sensors** — for basic obstacle detection and IR line following.
- **Accelerometer (optional)** — to estimate speed or movement changes.
- **Chassis with caster wheel** — robot body.

#### **Optional Expansion**
- **Raspberry Pi + Camera Module** — for future vision processing.
- **Shock-absorbing tank chassis** — for rough terrain movement.

---

## **Software Stack**

### **Embedded Layer (Arduino Code - C/C++)**
- Reads sensor data in real time.
- Executes motor commands (manual or calculated).
- Communicates with the laptop over Bluetooth serial.
- Responds to commands like `"auto_mode"`, `"turn_left"`, etc.

### **Robot Process (Laptop - Python)**
- Listens to incoming telemetry (sensor + encoder data).
- Sends parsed and structured commands to the Arduino.
- Processes controller input (manual mode).
- Handles autonomous navigation (pure pursuit algorithm).
- Communicates with backend (Flask API).

### **Backend Server (Python Flask)**
- Hosts API endpoints for the frontend.
- Handles natural language command parsing using GPT-4o via OpenAI API.
- Dispatches processed instructions to the robot process.

### **Frontend (Svelte, TypeScript, Tailwind CSS)**
- Provides a real-time GUI for robot status.
- Displays telemetry: position, speed, sensor data.
- Allows users to send manual instructions or natural language commands.
- Future addition: visual map path tracking.

---

## **AI Integration**
- A local or cloud-based LLM (GPT-4o via OpenAI API) interprets natural language instructions.
- The output is parsed into a structured command format.
- A secondary model can optionally validate or correct the parsed actions.
- Separate async loop avoids blocking robot behavior.

---

## **Modes of Operation**
- **Manual Mode:** User inputs (keyboard/controller) drive the robot directly.
- **Autonomous Mode:** Pure pursuit algorithm calculates motor commands based on a predefined or dynamically updated path.
- **AI Command Mode:** Natural language input is converted to robot-executable actions.

---

## **Key Features**
- Modular system split into **four distinct layers**: embedded (Arduino), robot logic (Python), backend (Flask), and frontend (Svelte).
- Efficient serial communication via Bluetooth for command-and-response loop.
- Future extensibility for camera vision and SLAM.
- Designed with both **educational** and **real-world robotics applications** in mind.

---

## **Skills Demonstrated**
- Embedded systems programming (Arduino C++)
- Bluetooth communication protocols
- Robotics algorithms (Pure Pursuit Path Following)
- Python systems engineering
- Flask API development
- AI integration via OpenAI API
- Frontend development with Svelte & Tailwind
- Real-time UI & telemetry visualization
- Multi-process architecture & IPC design
