import serial, eventlet

class SerialManager:
    def __init__(self, port='/dev/ttyUSB0', baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.connected = False

    def run_loop(self, robot):
        """
        Run a continuous loop reading from serial.
        This method is designed to be run in a separate thread.
        """
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=1)
            self.connected = True
            print(f"Connected to {self.port} at {self.baudrate} baud")

            buffer = ''

            while self.connected:
                if self.serial.in_waiting > 0:
                    try:
                        incoming = self.serial.read(self.serial.in_waiting).decode('utf-8')
                        buffer += incoming
            
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            line = line.strip()
                            if line:
                                try:
                                    robot.process_sensor_data(line)
                                except Exception as e:
                                    print(f"❌ Error processing sensor data: {e}")
                                    print(f"➡️  Raw data: {line!r}")
                    except UnicodeDecodeError as e:
                        print(f"❌ Decode error: {e}")
                        
                eventlet.sleep(0.01)
                        
        except Exception as e:
            self.connected = False
            print(f"Serial error: {e}")
            eventlet.sleep(5)
            self.run_loop(robot)  # Try to reconnect

    def send(self, data):
        """Send data over serial connection"""
        if not self.connected or not self.serial:
            print("Cannot send data - serial not connected")
            return False
            
        try:
            # Format data for sending
            if isinstance(data, str):
                # If it's a string, encode it to bytes
                formatted_data = data.encode('utf-8')
            elif hasattr(data, 'model_dump_json'):
                # If it's a pydantic model, convert it to JSON and then encode
                formatted_data = data.model_dump_json().encode('utf-8')
            else:
                # If it's already bytes, use as is
                formatted_data = data
                
            # Add newline if not present
            if not formatted_data.endswith(b'\n'):
                formatted_data += b'\n'
                
            # Send the data
            self.serial.write(formatted_data)
            self.serial.flush()  # Ensure data is sent immediately
            return True
            
        except Exception as e:
            print(f"Error sending data: {e}")
            self.connected = False
            return False