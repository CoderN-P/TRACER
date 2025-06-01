from pydantic import BaseModel, Field


class IMUData(BaseModel):
    """
    Represents the data from the IMU (Inertial Measurement Unit).
    """
    acceleration_x: float = Field(..., description="Acceleration in the X direction in m/s^2")
    acceleration_y: float = Field(..., description="Acceleration in the Y direction in m/s^2")
    acceleration_z: float = Field(..., description="Acceleration in the Z direction in m/s^2")
    gyroscope_x: float = Field(..., description="Angular velocity around the X axis in rad/s")
    gyroscope_y: float = Field(..., description="Angular velocity around the Y axis in rad/s")
    gyroscope_z: float = Field(..., description="Angular velocity around the Z axis in rad/s")
    temperature: float = Field(..., description="Temperature in degrees Celsius")