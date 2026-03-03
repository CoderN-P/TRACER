#include <QMC5883LCompass.h>
QMC5883LCompass compass;

void setup(){
  Serial.begin(115200);
  compass.setADDR(0x0D);
  compass.init();
}

void loop(){
  compass.read();
   int x = compass.getX();
   int y = compass.getY();
   int z = compass.getZ();
   Serial.println(String(x) + ", " + String(y) + ", " + String(z));
}