from pydantic import BaseModel, Field


class TOFData(BaseModel):
    """
    Represents the data from the IMU (Inertial Measurement Unit).
    """
    distance_front: float = Field(..., description="Distance measured by the front Time-of-Flight sensor in centimeters")