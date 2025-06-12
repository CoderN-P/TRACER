# Hardware Architecture

The main components of the hardware architecture are the raspberry Pi and arduino.
The raspberry Pi acts as the central processing unit, handling high-level logic, data processing, and communication with the web interface. It runs a Python application that processes incoming sensor data, makes decisions based on that data, and sends commands to the Arduino.

The Arduino is responsible for real-time hardware control and sensor management. It interfaces with the physical components of the robot, including motors, sensors, and displays. The Arduino handles low-level operations such as reading sensor data, controlling motor speeds, and managing communication with the Raspberry Pi via USB serial.


## Arduino Hardware Layer

### Components
- 2 **3 pin IR Sensors**: Used for cliff detection. 
  - **Front IR Sensor**: Detects cliffs in front of the robot. `pin 8`
  - **Back IR Sensor**: Detects cliffs behind the robot. `pin 12`
- **2x JGB37 DC Motors**: Provides movement capabilities for the robot.
- **1602 LCD with I2C Backpack**: Displays status messages and sensor data.
  - Connected to I2C address `0x27` (default for most I2C backpacks) using pins `SDA: A4`, `SCL: A5`.
- **MPU6050/9250 IMU**: Provides gyroscope and accelerometer data for motion sensing.
  - Connected to I2C address `0x68` using pins `SDA: A4`, `SCL: A5`.
- **TB6612FNG Motor Driver**: Controls the motors, allowing for speed and direction control via PWM signals.
  - PWMA: `pin 9`
  - PWMB: `pin 5`
  - AIN1: `pin 3`
  - AIN2: `pin 4`
  - BIN1: `pin 6`
  - BIN2: `pin 7`
  - STBY: `pin 13` (used for emergency stop)
- **HC-SR04 Ultrasonic Sensor**: Used for distance measurement.
  - TRIG: `pin 2`
  - ECHO: `pin 11`
- **Batteries**: Provides power to the motors and sensors.
  - 2x 18650 batteries in series for 7.4V (for motors)
  - Connected to VM pin of TB6612FNG and VIN pin of Arduino.
  - Also connected to arduino pin A3 for battery level measurement.