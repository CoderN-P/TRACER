#include <ESP32Servo.h>


Servo s;
int l = 0;
bool increment = true;

void setup() {
  // put your setup code here, to run once:
  
  s.attach(6);

}

void loop() {
  // put your main code here, to run repeatedly:
  if (increment){
    l += 10;
  } else {
    l -= 10;
  }
  s.write(l);
  if (l == 180){
    increment = false;
  }

  if (l == 0){
    increment = true;
  }
  delay(500);
}
