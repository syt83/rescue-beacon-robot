/*
  Rescue Beacon Robot - Arduino Nano Every MVP firmware

  USB Serial (RDK -> Arduino):
    CMD,<linear_mps>,<angular_radps>
    BEEP,1

  USB Serial telemetry (Arduino -> RDK):
    ENC,<left_count>,<right_count>

  IMPORTANT:
  - Confirm the MDD10A pins and motor inversion values against the real wiring.
  - This MVP maps cmd_vel to differential PWM. Encoder counts are reported, but
    closed-loop wheel PID is not enabled yet.
*/

#include <Arduino.h>

// ---------- MDD10A pin mapping: CHANGE TO MATCH REAL WIRING ----------
const uint8_t LEFT_PWM_PIN  = 5;
const uint8_t LEFT_DIR_PIN  = 4;
const uint8_t RIGHT_PWM_PIN = 6;
const uint8_t RIGHT_DIR_PIN = 7;

// ---------- Encoder pin mapping: CHANGE TO MATCH REAL WIRING ----------
const uint8_t LEFT_ENC_A_PIN  = 2;
const uint8_t LEFT_ENC_B_PIN  = 8;
const uint8_t RIGHT_ENC_A_PIN = 3;
const uint8_t RIGHT_ENC_B_PIN = 9;

// Flip these if a motor rotates in the wrong direction.
const bool LEFT_MOTOR_INVERT  = false;
const bool RIGHT_MOTOR_INVERT = true;

// Command scaling. Tune on the real chassis.
const float MAX_LINEAR_CMD  = 0.20f;  // m/s represented by 100% forward PWM
const float MAX_ANGULAR_CMD = 0.70f;  // rad/s represented by 100% turn mix
const uint8_t MAX_PWM = 180;          // conservative initial limit (0..255)

const unsigned long COMMAND_TIMEOUT_MS = 500;
const unsigned long TELEMETRY_PERIOD_MS = 200;

// DFPlayer Pro on Nano Every hardware UART Serial1.
// Nano Every: RX1/TX1 are the hardware UART pins. Verify board pin labels.
const uint32_t DFPLAYER_BAUD = 115200;
const uint8_t DFPLAYER_VOLUME = 20;  // 0..30
const int DFPLAYER_ALERT_FILE_NUMBER = 1;

volatile long leftEncoderCount = 0;
volatile long rightEncoderCount = 0;

unsigned long lastCommandMs = 0;
unsigned long lastTelemetryMs = 0;

String inputLine;


float clampf(float x, float lo, float hi) {
  if (x < lo) return lo;
  if (x > hi) return hi;
  return x;
}


void leftEncoderISR() {
  bool b = digitalRead(LEFT_ENC_B_PIN);
  leftEncoderCount += b ? 1 : -1;
}


void rightEncoderISR() {
  bool b = digitalRead(RIGHT_ENC_B_PIN);
  rightEncoderCount += b ? 1 : -1;
}


void setOneMotor(uint8_t pwmPin, uint8_t dirPin, float command, bool invert) {
  command = clampf(command, -1.0f, 1.0f);
  if (invert) command = -command;

  bool forward = command >= 0.0f;
  uint8_t pwm = (uint8_t)(fabs(command) * MAX_PWM);

  digitalWrite(dirPin, forward ? HIGH : LOW);
  analogWrite(pwmPin, pwm);
}


void stopMotors() {
  analogWrite(LEFT_PWM_PIN, 0);
  analogWrite(RIGHT_PWM_PIN, 0);
}


void applyCmdVel(float linear, float angular) {
  float forward = linear / MAX_LINEAR_CMD;
  float turn = angular / MAX_ANGULAR_CMD;

  // ROS convention: +angular.z = left turn.
  float left = forward - turn;
  float right = forward + turn;

  float peak = max(fabs(left), fabs(right));
  if (peak > 1.0f) {
    left /= peak;
    right /= peak;
  }

  setOneMotor(
    LEFT_PWM_PIN, LEFT_DIR_PIN, left, LEFT_MOTOR_INVERT
  );
  setOneMotor(
    RIGHT_PWM_PIN, RIGHT_DIR_PIN, right, RIGHT_MOTOR_INVERT
  );
}


void dfSend(const String &cmd) {
  Serial1.print(cmd);
  Serial1.print("\r\n");
}


void playAlert() {
  dfSend("AT+PLAYNUM=" + String(DFPLAYER_ALERT_FILE_NUMBER));
}


void processCommand(String line) {
  line.trim();

  if (line.startsWith("CMD,")) {
    int comma1 = line.indexOf(',');
    int comma2 = line.indexOf(',', comma1 + 1);

    if (comma2 > comma1) {
      float linear = line.substring(comma1 + 1, comma2).toFloat();
      float angular = line.substring(comma2 + 1).toFloat();

      applyCmdVel(linear, angular);
      lastCommandMs = millis();
    }
    return;
  }

  if (line == "BEEP,1") {
    playAlert();
    return;
  }
}


void setup() {
  pinMode(LEFT_PWM_PIN, OUTPUT);
  pinMode(LEFT_DIR_PIN, OUTPUT);
  pinMode(RIGHT_PWM_PIN, OUTPUT);
  pinMode(RIGHT_DIR_PIN, OUTPUT);

  pinMode(LEFT_ENC_A_PIN, INPUT_PULLUP);
  pinMode(LEFT_ENC_B_PIN, INPUT_PULLUP);
  pinMode(RIGHT_ENC_A_PIN, INPUT_PULLUP);
  pinMode(RIGHT_ENC_B_PIN, INPUT_PULLUP);

  attachInterrupt(
    digitalPinToInterrupt(LEFT_ENC_A_PIN), leftEncoderISR, CHANGE
  );
  attachInterrupt(
    digitalPinToInterrupt(RIGHT_ENC_A_PIN), rightEncoderISR, CHANGE
  );

  stopMotors();

  // USB serial to RDK X5.
  Serial.begin(115200);

  // Hardware UART to DFPlayer Pro.
  Serial1.begin(DFPLAYER_BAUD);
  delay(300);
  dfSend("AT");
  dfSend("AT+VOL=" + String(DFPLAYER_VOLUME));
  dfSend("AT+PLAYMODE=3");  // play one file then pause

  lastCommandMs = millis();
  lastTelemetryMs = millis();
}


void loop() {
  while (Serial.available()) {
    char c = (char)Serial.read();

    if (c == '\n') {
      processCommand(inputLine);
      inputLine = "";
    } else if (c != '\r') {
      if (inputLine.length() < 96) {
        inputLine += c;
      } else {
        inputLine = "";
      }
    }
  }

  // Fail-safe: stop if RDK command stream disappears.
  if (millis() - lastCommandMs > COMMAND_TIMEOUT_MS) {
    stopMotors();
  }

  if (millis() - lastTelemetryMs >= TELEMETRY_PERIOD_MS) {
    noInterrupts();
    long left = leftEncoderCount;
    long right = rightEncoderCount;
    interrupts();

    Serial.print("ENC,");
    Serial.print(left);
    Serial.print(",");
    Serial.println(right);

    lastTelemetryMs = millis();
  }
}
