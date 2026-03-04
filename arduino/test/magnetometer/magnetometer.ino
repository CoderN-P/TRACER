#include <Wire.h>

float LSB_uT = 0.0244; // ±8G full-scale

void setup(){
  Serial.begin(115200);
  Wire.begin();
  setup_magnetometer();
}

void setup_magnetometer(){
  uint8_t MODE_CONTINUOUS = 0b00000001;
  uint8_t ODR_50Hz = 0b00000100;
  uint8_t LSB_8G = 0b00010000;
  uint8_t OSR_512 = 0x00;
  Wire.beginTransmission(0x0D);
  Wire.write(0x09);
  Wire.write(MODE_CONTINUOUS | ODR_50Hz | LSB_8G | OSR_512);
  Wire.endTransmission();
}

void loop(){
  Wire.beginTransmission(0x0D);
  Wire.write(0x00);
  Wire.endTransmission(false);
  Wire.requestFrom(0x0D, 6);

  uint16_t x_u =  (uint16_t)(Wire.read() | (Wire.read() << 8)); // LSB comes first
  uint16_t y_u =  (uint16_t)(Wire.read() | (Wire.read() << 8));
  uint16_t z_u =  (uint16_t)(Wire.read() | (Wire.read() << 8));

  float x = ((int16_t) x_u) * LSB_uT;
  float y = ((int16_t) y_u) * LSB_uT;
  float z = ((int16_t) z_u) * LSB_uT;


   Serial.println(String(x) + ", " + String(y) + ", " + String(z));
   // Wire.endTransmission( );
   delay(50);
}