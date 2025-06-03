from pydantic import BaseModel, Field


class LCDCommand(BaseModel):
    """
    Represents a command to control the LCD display.
    """
    line_1: str = Field(..., description="Text to display on the first line of the LCD")
    line_2: str = Field(..., description="Text to display on the second line of the LCD")
    
   