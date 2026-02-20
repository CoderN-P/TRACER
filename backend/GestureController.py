"""
Recieves and processes accelerometer data from esp32 dev board and converts to joystick commands.
"""
import threading

import requests, time, math
from GestureData import GestureData

class GestureController:
    def __init__(self, url, socketio):
        self.api_url = url
        self.last_query_time = 0
        self.query_interval = 0.1  # seconds between emits - 10hz 
        self.data = GestureData()
        self.socketio = socketio # socketio server

    @staticmethod
    def accelerometer_to_joystick(pitch, roll):
        pitch = max(-80, min(pitch, 80))
        roll  = max(-80, min(roll, 80))
    
        x = abs(roll / 80)**0.9 * (-1 if roll > 0 else 1) # Roll controls turning (x-axis)
        y = abs(pitch / 80)**0.9 * (-1 if pitch > 0 else 1) # Pitch controls forward/backward (y-axis)
    
        if abs(x) < 0.05: x = 0
        if abs(y) < 0.05: y = 0
        
        if abs(y) > 0.4:
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
    
                        self.socketio.emit('gesture_data', self.data.model_dump())
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
        
        pitch = self.data.mag_angles.pitch
        roll = self.data.mag_angles.roll
        
        y, x = self.accelerometer_to_joystick(pitch, roll)
        
        # Check if the joystick input is significant enough to send an update
        if abs(y) > 0 or abs(x) > 0:
            return True
    
    def get_joystick_input(self):
        """
        Get joystick input based on accelerometer data.
        :return: Tuple of (left_y, right_x) for joystick axes
        """
        pitch = self.data.mag_angles.pitch
        roll = self.data.mag_angles.roll
        
        return self.accelerometer_to_joystick(pitch, roll)
            
            
        