/*
  Rescue Beacon Robot - Arduino Nano Every, protocol version 1.

  USB Serial at 115200 baud:
    RDK -> Nano: HELLO | CMD,<linear_mps>,<angular_radps> | BEEP,1
    Nano -> RDK: READY,1 | ENC,<left_count>,<right_count> |
                 SOUND,<0_or_1> | ACK,BEEP | ERR,CMD

  The motor and encoder pins below are the proposed wiring map. Check the
  physical wiring and wheel direction before applying motor power.
*/

#include <Arduino.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

// Cytron MDD10A, PWM/DIR mode. D5 and D6 are PWM pins on Nano Every.
const uint8_t LEFT_PWM_PIN = 5;
const uint8_t LEFT_DIR_PIN = 4;
const uint8_t RIGHT_PWM_PIN = 6;
const uint8_t RIGHT_DIR_PIN = 7;

// Encoder A inputs use interrupts. B inputs are sampled in the ISRs.
const uint8_t LEFT_ENC_A_PIN = 2;
const uint8_t LEFT_ENC_B_PIN = 8;
const uint8_t RIGHT_ENC_A_PIN = 3;
const uint8_t RIGHT_ENC_B_PIN = 9;

// LM393 digital output. A single sensor detects sound, not its direction.
const uint8_t SOUND_PIN = 10;
const bool SOUND_ACTIVE_LOW = true;

// Check these signs with the wheels off the ground.
const bool LEFT_MOTOR_INVERT = false;
const bool RIGHT_MOTOR_INVERT = true;

const float MAX_LINEAR_CMD = 0.20f;
const float MAX_ANGULAR_CMD = 0.70f;
const uint8_t MAX_PWM = 180;
const unsigned long COMMAND_TIMEOUT_MS = 500;
const unsigned long TELEMETRY_PERIOD_MS = 200;

// DFPlayer Mini, not DFPlayer Pro. Serial1 uses Nano Every RX/TX pins.
const uint32_t DFPLAYER_BAUD = 9600;
const uint8_t DFPLAYER_VOLUME = 20;  // 0..30
const uint16_t ALERT_FILE_NUMBER = 1;  // SD card: /mp3/0001.mp3

volatile long leftEncoderCount = 0;
volatile long rightEncoderCount = 0;
unsigned long lastCommandMs = 0;
unsigned long lastTelemetryMs = 0;
char inputLine[64];
uint8_t inputLength = 0;
bool discardLine = false;


float clampf(float value, float low, float high) {
  if (value < low) return low;
  if (value > high) return high;
  return value;
}


void leftEncoderISR() {
  leftEncoderCount += digitalRead(LEFT_ENC_B_PIN) ? 1 : -1;
}


void rightEncoderISR() {
  rightEncoderCount += digitalRead(RIGHT_ENC_B_PIN) ? 1 : -1;
}


void stopMotors() {
  analogWrite(LEFT_PWM_PIN, 0);
  analogWrite(RIGHT_PWM_PIN, 0);
}


void setOneMotor(uint8_t pwmPin, uint8_t dirPin, float command, bool invert) {
  command = clampf(command, -1.0f, 1.0f);
  if (invert) command = -command;
  digitalWrite(dirPin, command >= 0.0f ? HIGH : LOW);
  analogWrite(pwmPin, (uint8_t)(fabs(command) * MAX_PWM));
}


void applyCmdVel(float linear, float angular) {
  float left = linear / MAX_LINEAR_CMD - angular / MAX_ANGULAR_CMD;
  float right = linear / MAX_LINEAR_CMD + angular / MAX_ANGULAR_CMD;
  float peak = max(fabs(left), fabs(right));
  if (peak > 1.0f) {
    left /= peak;
    right /= peak;
  }
  setOneMotor(LEFT_PWM_PIN, LEFT_DIR_PIN, left, LEFT_MOTOR_INVERT);
  setOneMotor(RIGHT_PWM_PIN, RIGHT_DIR_PIN, right, RIGHT_MOTOR_INVERT);
}


// DFRobot DFPlayer Mini 10-byte serial frame. Feedback is disabled.
void dfSend(uint8_t command, uint16_t parameter) {
  uint8_t frame[10] = {
    0x7E, 0xFF, 0x06, command, 0x00,
    (uint8_t)(parameter >> 8), (uint8_t)parameter,
    0x00, 0x00, 0xEF
  };
  uint16_t sum = 0;
  for (uint8_t i = 1; i <= 6; ++i) sum += frame[i];
  uint16_t checksum = (uint16_t)(0 - sum);
  frame[7] = (uint8_t)(checksum >> 8);
  frame[8] = (uint8_t)checksum;
  Serial1.write(frame, sizeof(frame));
}


void playAlert() {
  dfSend(0x06, DFPLAYER_VOLUME);
  delay(20);
  // 0x12 selects a numbered file in /mp3, independent of copy order.
  dfSend(0x12, ALERT_FILE_NUMBER);
  Serial.println(F("ACK,BEEP"));
}


bool parseCmd(char *text, float *linear, float *angular) {
  char *comma = strchr(text, ',');
  if (comma == NULL) return false;
  *comma = '\0';
  char *end = NULL;
  double v = strtod(text, &end);
  if (end == text || *end != '\0' || isnan(v) || isinf(v)) return false;
  char *angularText = comma + 1;
  double w = strtod(angularText, &end);
  if (end == angularText || *end != '\0' || isnan(w) || isinf(w)) return false;
  if (fabs(v) > MAX_LINEAR_CMD || fabs(w) > MAX_ANGULAR_CMD) return false;
  *linear = (float)v;
  *angular = (float)w;
  return true;
}


void processCommand(char *line) {
  if (strcmp(line, "HELLO") == 0) {
    Serial.println(F("READY,1"));
    return;
  }
  if (strcmp(line, "BEEP,1") == 0) {
    playAlert();
    return;
  }
  if (strncmp(line, "CMD,", 4) == 0) {
    float linear = 0.0f;
    float angular = 0.0f;
    if (!parseCmd(line + 4, &linear, &angular)) {
      stopMotors();
      Serial.println(F("ERR,CMD"));
      return;
    }
    applyCmdVel(linear, angular);
    lastCommandMs = millis();
  }
}


void setup() {
  pinMode(LEFT_PWM_PIN, OUTPUT);
  pinMode(LEFT_DIR_PIN, OUTPUT);
  pinMode(RIGHT_PWM_PIN, OUTPUT);
  pinMode(RIGHT_DIR_PIN, OUTPUT);
  stopMotors();

  pinMode(LEFT_ENC_A_PIN, INPUT_PULLUP);
  pinMode(LEFT_ENC_B_PIN, INPUT_PULLUP);
  pinMode(RIGHT_ENC_A_PIN, INPUT_PULLUP);
  pinMode(RIGHT_ENC_B_PIN, INPUT_PULLUP);
  pinMode(SOUND_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(LEFT_ENC_A_PIN), leftEncoderISR, CHANGE);
  attachInterrupt(digitalPinToInterrupt(RIGHT_ENC_A_PIN), rightEncoderISR, CHANGE);

  Serial.begin(115200);
  Serial1.begin(DFPLAYER_BAUD);
  delay(3000);  // Allow the DFPlayer Mini and its SD card to boot.
  dfSend(0x06, DFPLAYER_VOLUME);

  lastCommandMs = millis();
  lastTelemetryMs = millis();
  Serial.println(F("READY,1"));
}


void loop() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n') {
      if (!discardLine) {
        inputLine[inputLength] = '\0';
        processCommand(inputLine);
      }
      inputLength = 0;
      discardLine = false;
    } else if (c != '\r' && !discardLine) {
      if (inputLength < sizeof(inputLine) - 1) {
        inputLine[inputLength++] = c;
      } else {
        inputLength = 0;
        discardLine = true;
        stopMotors();
        Serial.println(F("ERR,LINE"));
      }
    }
  }

  if (millis() - lastCommandMs > COMMAND_TIMEOUT_MS) stopMotors();

  if (millis() - lastTelemetryMs >= TELEMETRY_PERIOD_MS) {
    noInterrupts();
    long left = leftEncoderCount;
    long right = rightEncoderCount;
    interrupts();
    Serial.print(F("ENC,"));
    Serial.print(left);
    Serial.print(',');
    Serial.println(right);
    bool sound = digitalRead(SOUND_PIN) == (SOUND_ACTIVE_LOW ? LOW : HIGH);
    Serial.print(F("SOUND,"));
    Serial.println(sound ? 1 : 0);
    lastTelemetryMs = millis();
  }
}
