from pydantic import BaseModel, Field


class MagnetometerData(BaseModel):
    x: float = Field(..., description="Magnetic field strength in the X direction in microteslas (µT)")
    y: float = Field(..., description="Magnetic field strength in the Y direction in microteslas (µT)")
    z: float = Field(..., description="Magnetic field strength in the Z direction in microteslas (µT)")
    heading: float = Field(..., description="Heading calculated from magnetometer data in degrees")
    
    @staticmethod
    def calculate_heading(x, y, z) -> float:
        # TODO: Implement heading calculation based on x and y magnetometer readings with hard and soft iron calibration
        pass 