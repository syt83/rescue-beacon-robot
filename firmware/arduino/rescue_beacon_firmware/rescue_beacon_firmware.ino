/*
  구조 비콘 로봇 - Arduino Nano Every, 직렬 프로토콜 버전 1.

  USB Serial, 115200 baud:
    RDK -> Nano: HELLO | CMD,<linear_mps>,<angular_radps> | BEEP,1
    Nano -> RDK: READY,1 | ENC,<left_count>,<right_count> |
                 SOUND,<0_or_1> | ACK,BEEP | ERR,CMD

  아래 핀은 배선 제안이다. 모터 전원을 넣기 전에 실제 연결과 바퀴 방향을 확인한다.
*/

#include <Arduino.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

// Cytron MDD10A의 PWM/DIR 모드. Nano Every의 D5와 D6는 PWM 출력 핀이다.
const uint8_t LEFT_PWM_PIN = 5;
const uint8_t LEFT_DIR_PIN = 4;
const uint8_t RIGHT_PWM_PIN = 6;
const uint8_t RIGHT_DIR_PIN = 7;

// 엔코더 A 변화는 인터럽트로 세고, 그 순간의 B 값으로 회전 방향을 정한다.
const uint8_t LEFT_ENC_A_PIN = 2;
const uint8_t LEFT_ENC_B_PIN = 8;
const uint8_t RIGHT_ENC_A_PIN = 3;
const uint8_t RIGHT_ENC_B_PIN = 9;

// LM393 디지털 출력. 센서 한 개로는 소리 유무만 알고 방향은 알 수 없다.
const uint8_t SOUND_PIN = 10;
const bool SOUND_ACTIVE_LOW = true;

// 바퀴를 지면에서 띄우고 전진 명령 방향을 확인한 뒤 반전 값을 조정한다.
const bool LEFT_MOTOR_INVERT = false;
const bool RIGHT_MOTOR_INVERT = true;

const float MAX_LINEAR_CMD = 0.20f;
const float MAX_ANGULAR_CMD = 0.70f;
const uint8_t MAX_PWM = 180;
const unsigned long COMMAND_TIMEOUT_MS = 500;
const unsigned long TELEMETRY_PERIOD_MS = 200;

// DFPlayer Mini용 설정. Serial1은 Nano Every의 RX/TX 핀을 사용한다.
const uint32_t DFPLAYER_BAUD = 9600;
const uint8_t DFPLAYER_VOLUME = 20;  // 볼륨 범위: 0..30
const uint16_t ALERT_FILE_NUMBER = 1;  // SD 카드 파일: /mp3/0001.mp3

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
  // ROS의 전진 속도와 회전 속도를 좌우 바퀴 출력 비율로 변환한다.
  // peak 정규화로 어느 쪽도 PWM 상한을 넘지 않게 한다.
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


// DFPlayer Mini의 10바이트 직렬 프레임을 직접 만든다. 응답 요청은 끈다.
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
  // 0x12는 파일 복사 순서와 관계없이 /mp3의 번호로 음원을 선택한다.
  dfSend(0x12, ALERT_FILE_NUMBER);
  // 이 응답은 재생 요청 전달 성공만 뜻한다. 실제 소리는 별도로 확인한다.
  Serial.println(F("ACK,BEEP"));
}


bool parseCmd(char *text, float *linear, float *angular) {
  // 숫자 형식, NaN/무한대, 허용 속도 범위를 모두 검사한다.
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
  // USB 호스트는 HELLO에 대한 READY,1을 확인한 뒤 명령을 보낸다.
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
      // 잘못된 CMD를 받으면 기존 주행을 즉시 중단한다.
      stopMotors();
      Serial.println(F("ERR,CMD"));
      return;
    }
    applyCmdVel(linear, angular);
    lastCommandMs = millis();
  }
}


void setup() {
  // 부팅 직후 모터 PWM을 0으로 두고 입력·출력을 초기화한다.
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
  delay(3000);  // DFPlayer Mini와 SD 카드가 부팅할 시간을 준다.
  dfSend(0x06, DFPLAYER_VOLUME);

  lastCommandMs = millis();
  lastTelemetryMs = millis();
  Serial.println(F("READY,1"));
}


void loop() {
  // 너무 긴 직렬 입력은 버리고 모터를 멈춘다.
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

  // 0.5초 동안 유효한 CMD가 오지 않으면 PWM을 0으로 만든다.
  if (millis() - lastCommandMs > COMMAND_TIMEOUT_MS) stopMotors();

  if (millis() - lastTelemetryMs >= TELEMETRY_PERIOD_MS) {
    // 인터럽트 중간에 32비트 카운트를 읽지 않도록 잠깐 잠근다.
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
