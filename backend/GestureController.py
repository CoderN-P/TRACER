"""
Recieves and processes accelerometer data from esp32 dev board and converts to joystick commands.
"""
import threading

import requests, time, math
from GestureData import GestureData

class GestureController:
    def __init__(self, url):
        self.api_url = url
        self.last_query_time = 0
        self.query_interval = 0.1  # seconds between emits - 10hz 
        self.data = GestureData()

    @staticmethod
    def accelerometer_to_joystick(ax, ay, az):
        norm = math.sqrt(ax**2 + ay**2 + az**2)
        ax /= norm or 1
        ay /= norm or 1
        az /= norm or 1
    
        pitch = math.degrees(math.atan2(ax, math.sqrt(ay**2 + az**2)))
        roll  = math.degrees(math.atan2(ay, az))
    
        pitch = max(-60, min(pitch, 60))
        roll  = max(-60, min(roll, 60))
    
        x = -roll / 60
        y = pitch / 60 
    
        if abs(x) < 0.2: x = 0
        if abs(y) < 0.2: y = 0
        
        if abs(y) > 0.5:
            x = x if abs(x) > 0.4 else 0 # If y is significant, ignore x unless it's also significant
    
        return y, x # Treat like joystick axes
            
    def _sensor_request_loop(self):
        while True:
            current_time = time.time()
            if current_time - self.last_query_time >= self.query_interval:
                try:
                    response = requests.get(self.api_url)
                    if response.status_code == 200:
                        self.data = GestureData.model_validate(response.json())
                        self.last_query_time = current_time
                    else:
                        print(f"Failed to fetch data: {response.status_code}")
                except requests.RequestException as e:
                    print(f"Error fetching sensor data: {e}")
            time.sleep(0.1)
            
    def start_sensor_loop(self):
        """
        Start the sensor request loop in a separate thread.
        """
        threading.Thread(target=self._sensor_request_loop, daemon=True).start()
    
    def should_send_update(self):
        """
        Check if board is at rest (i.e. no significant movement) or is moving and should send an update.
        :return: 
        """
        
        if not self.data:
            return False
        
        ax = self.data.accelerometer.x
        ay = self.data.accelerometer.y
        az = self.data.accelerometer.z
        
        y, x = self.accelerometer_to_joystick(ax, ay, az)
        
        # Check if the joystick input is significant enough to send an update
        if abs(y) > 0 or abs(x) > 0:
            return True
    
    def get_joystick_input(self):
        """
        Get joystick input based on accelerometer data.
        :return: Tuple of (left_y, right_x) for joystick axes
        """
        ax = self.data.accelerometer.x
        ay = self.data.accelerometer.y
        az = self.data.accelerometer.z
        
        return self.accelerometer_to_joystick(ax, ay, az)
            
            
        