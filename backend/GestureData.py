from pydantic import BaseModel
import math

class AccelerometerData(BaseModel):
    """
    Represents accelerometer data from wireless sifive board. Units are Gs
    """
    
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    
    
class AmbientLightData(BaseModel):
    """
    Represents ambient light data from wireless sifive board.
    """
    
    lux: float = 0.0
    ch0: int = 0
    ch1: int = 0
    
class MagnetometerData(BaseModel):
    """
    Represents magnetometer data from wireless sifive board.
    """
    
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    

class MagnetomerAngleData(BaseModel):
    """
    Represents magnetometer angle data from wireless sifive board.
    """
    
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
   

class GestureData(BaseModel):
    """
    Represents gesture data from wireless sifive board.
    """
    
    temperature: float = 0.0
    accelerometer: AccelerometerData = AccelerometerData()
    light: AmbientLightData = AmbientLightData()
    magnetometer: MagnetometerData = MagnetometerData()
    mag_angles: MagnetomerAngleData = MagnetomerAngleData()
    
    
    
        
        
        
        
        
    


    
    
