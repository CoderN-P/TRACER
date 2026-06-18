from pydantic import BaseModel, Field


class ConfigCommand(BaseModel):
    """
    Represents a command to update the embedded config.
    """
    P_LEFT: float | None = Field(default=None, description="P term in left motor PID controller")
    P_RIGHT: float | None = Field(default=None, description="P term in right motor PID controller")
    I_LEFT: float | None = Field(default=None, description="I term in left motor PID controller")
    I_RIGHT: float | None = Field(default=None, description="I term in right motor PID controller")
    D_LEFT: float | None = Field(default=None, description="D term in left motor PID controller")
    D_RIGHT: float | None = Field(default=None, description="D term in right motor PID controller")
    I_ZONE: float | None = Field(default=None, description="Error zone in which to add error")
    NOMINAL_WHEEL_BASE: float | None = Field(default=None, description="Wheel base to use when not using adaptive wheel base")
    WHEEL_BASE_MAX: float | None = Field(default=None, description="Max wheel base")
    WHEEL_BASE_MIN: float | None = Field(default=None, description="Min wheel base")
    ALPHA: float | None = Field(default=None, description="Alpha value for adaptive wheel base")
    USE_GYRO_CORRECTION: bool | None = Field(default=None, description="Whether to use gyro correction on top of velocity PID")
    USE_ADAPTIVE_WHEEL_BASE: bool | None = Field(default=None, description="Whether to use adaptive wheel base or nominal wheel base")
    LEFT_CORRECTION_POS: float | None = Field(default=None, description="Left meters per tick correction for positive tick delta")
    RIGHT_CORRECTION_POS: float | None = Field(default=None, description="Right meters per tick correction for positive tick delta")
    LEFT_CORRECTION_NEG: float | None = Field(default=None, description="Left meters per tick correction for negative tick delta")
    RIGHT_CORRECTION_NEG: float | None = Field(default=None, description="Right meters per tick correction for negative tick delta")

