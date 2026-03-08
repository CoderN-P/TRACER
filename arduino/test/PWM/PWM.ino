
// Test script to determine minimum PWM value for motors
// Users enter a PWM value for the motors to run at for 1 second. 

const int EN1 = 26; // Enable pin for motor 1 - wired
const int IN1 = 18; // Input pin 1 for motor 1  - wired
const int IN2 = 33; // Input pin 2 for motor 1  - wired
const int EN2 = 32; // Enable pin for motor 2 - wired
const int IN3 = 25; // Input pin 1 for motor 2  - wired
const int IN4 = 19; // Input pin 2 for motor 2 - wired

void setup() {
    Serial.begin(115200);
    pinMode(EN1, OUTPUT);
    pinMode(IN1, OUTPUT);
    pinMode(IN2, OUTPUT);
    pinMode(EN2, OUTPUT);
    pinMode(IN3, OUTPUT);
    pinMode(IN4, OUTPUT);
    
    while (!Serial) {
    ; // Wait for serial port to connect.
    }
    Serial.println("Enter a PWM value between 0 and 4095 to test motor response:");
}

void handleMovement(int left, int right){
{
    if (left > 0)
    {
        digitalWrite(IN1, HIGH);
        digitalWrite(IN2, LOW);
        ledcWrite(EN1, left);
    }
    else if (left < 0)
    {
        digitalWrite(IN1, LOW);
        digitalWrite(IN2, HIGH);
        ledcWrite(EN1, -left);
    }
    else
    {
        digitalWrite(IN1, LOW);
        digitalWrite(IN2, LOW);
        ledcWrite(EN1, 0);
    }

    if (right > 0)
    {
        digitalWrite(IN3, HIGH);
        digitalWrite(IN4, LOW);
        ledcWrite(EN2, right);
    }
    else if (right < 0)
    {
        digitalWrite(IN3, LOW);
        digitalWrite(IN4, HIGH);
        ledcWrite(EN2, -right);
    }
    else
    {
        digitalWrite(IN3, LOW);
        digitalWrite(IN4, LOW);
        ledcWrite(EN2, 0);
    }
}
void loop() {
  if (Serial.available() > 0) {
    int pwmValue = Serial.parseInt();
    if (pwmValue >= 0 && pwmValue <= 4095) {
      Serial.print("Testing PWM value: ");
      Serial.println(pwmValue);
      handleMovement(pwmValue, pwmValue); // Run both motors at the same PWM value
      delay(1000); // Run the motors for 1 second
      handleMovement(0, 0);
      Serial.println("Test complete. Enter another PWM value:");
    } else {
      Serial.println("Invalid PWM value. Please enter a value between 0 and 4095:");
    }
  }
}

