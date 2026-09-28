/*
  Nano Every + MD20A 2개: 모터만 분리해서 확인하는 임시 스케치.

  업로드와 USB 연결은 모터 배터리 스위치를 끈 상태에서 한다.
  부팅 시 자동 구동하지 않는다. 시리얼 모니터 115200 baud, Newline 설정:
    STATUS -> 현재 명령 상태 확인 (모터 구동 없음)
    ARM    -> 5초 동안 다음 LEFT 또는 RIGHT 명령 한 번 허용
    LEFT   -> 왼쪽만 PWM 60/255로 0.2초 구동
    RIGHT  -> 오른쪽만 PWM 60/255로 0.2초 구동
    STOP   -> 두 PWM 출력을 즉시 0으로 설정

  이 스케치는 MD20A에 실제로 들어간 전압이나 바퀴 정지를 측정하지 못한다.
  명령 없이 바퀴가 돌거나 STOP 후에도 돌면 메인 스위치를 즉시 끈다.
*/

#include <Arduino.h>
#include <string.h>

// 공유 회로도 Arduino_Core와 구조 로봇 본 펌웨어의 핀 배치를 그대로 쓴다.
const uint8_t LEFT_PWM_PIN = 3;
const uint8_t LEFT_DIR_PIN = 4;
const uint8_t RIGHT_PWM_PIN = 9;
const uint8_t RIGHT_DIR_PIN = 7;

// 본 펌웨어의 전진 방향 설정과 같다. 실제 전진 여부는 눈으로 확인한다.
const uint8_t LEFT_FORWARD_LEVEL = HIGH;
const uint8_t RIGHT_FORWARD_LEVEL = LOW;
const uint8_t TEST_PWM = 60;                 // 0..255 중 낮은 출력
const unsigned long TEST_TIME_MS = 200;    // 한 번에 최대 0.2초
const unsigned long ARM_TIME_MS = 5000;    // ARM 뒤 5초 이내에만 구동

bool armed = false;
bool pulseActive = false;
unsigned long armedAtMs = 0;
unsigned long pulseStartedMs = 0;
char inputLine[16];
uint8_t inputLength = 0;
bool discardLine = false;


void stopMotors() {
  // Nano Every의 analogWrite(pin, 0)은 출력 LOW로 전환한다.
  analogWrite(LEFT_PWM_PIN, 0);
  analogWrite(RIGHT_PWM_PIN, 0);
  digitalWrite(LEFT_PWM_PIN, LOW);
  digitalWrite(RIGHT_PWM_PIN, LOW);
  pulseActive = false;
}


void startPulse(bool left) {
  // ARM은 구동 한 번에만 적용한다. 반대쪽 PWM은 먼저 0으로 만든다.
  armed = false;
  stopMotors();
  if (left) {
    digitalWrite(LEFT_DIR_PIN, LEFT_FORWARD_LEVEL);
    Serial.println(F("COMMAND,LEFT,200MS"));
  } else {
    digitalWrite(RIGHT_DIR_PIN, RIGHT_FORWARD_LEVEL);
    Serial.println(F("COMMAND,RIGHT,200MS"));
  }
  pulseStartedMs = millis();
  pulseActive = true;
  // 직렬 출력이 지연되더라도 그 시간이 0.2초 제한에 더해지지 않도록 한다.
  analogWrite(left ? LEFT_PWM_PIN : RIGHT_PWM_PIN, TEST_PWM);
}


void processLine(const char *line) {
  if (strcmp(line, "STOP") == 0) {
    armed = false;
    stopMotors();
    Serial.println(F("PWM_ZERO_COMMAND"));
  } else if (strcmp(line, "STATUS") == 0) {
    Serial.println(pulseActive ? F("STATUS,PULSE_ACTIVE") : F("STATUS,IDLE"));
  } else if (strcmp(line, "ARM") == 0) {
    stopMotors();
    armed = true;
    armedAtMs = millis();
    Serial.println(F("ARMED,5S,ONE_PULSE"));
  } else if (strcmp(line, "LEFT") == 0 || strcmp(line, "RIGHT") == 0) {
    if (!armed || millis() - armedAtMs > ARM_TIME_MS) {
      armed = false;
      stopMotors();
      Serial.println(F("NOT_ARMED"));
      return;
    }
    startPulse(strcmp(line, "LEFT") == 0);
  } else {
    armed = false;
    stopMotors();
    Serial.println(F("UNKNOWN_COMMAND,PWM_ZERO"));
  }
}


void setup() {
  // 출력 모드로 바꾸기 전에 LOW를 래치한다. 부팅 시 자동 구동은 없다.
  digitalWrite(LEFT_PWM_PIN, LOW);
  digitalWrite(RIGHT_PWM_PIN, LOW);
  digitalWrite(LEFT_DIR_PIN, LOW);
  digitalWrite(RIGHT_DIR_PIN, LOW);
  pinMode(LEFT_PWM_PIN, OUTPUT);
  pinMode(RIGHT_PWM_PIN, OUTPUT);
  pinMode(LEFT_DIR_PIN, OUTPUT);
  pinMode(RIGHT_DIR_PIN, OUTPUT);
  stopMotors();
  Serial.begin(115200);
  Serial.println(F("MOTOR_ONLY_READY; SEND STATUS"));
}


void loop() {
  // 구동 중에도 입력을 받아 STOP을 처리하고, 0.2초가 지나면 자동으로 끈다.
  if (pulseActive && millis() - pulseStartedMs >= TEST_TIME_MS) {
    stopMotors();
    Serial.println(F("PWM_ZERO_COMMAND; VERIFY_WHEEL_STOPPED"));
  }
  if (armed && millis() - armedAtMs > ARM_TIME_MS) {
    armed = false;
    Serial.println(F("ARM_EXPIRED"));
  }

  while (Serial.available()) {
    // 입력이 연속해서 들어오는 중에도 구동 시간 상한을 확인한다.
    if (pulseActive && millis() - pulseStartedMs >= TEST_TIME_MS) {
      stopMotors();
      Serial.println(F("PWM_ZERO_COMMAND; VERIFY_WHEEL_STOPPED"));
    }
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (!discardLine && inputLength > 0) {
        inputLine[inputLength] = '\0';
        processLine(inputLine);
      }
      inputLength = 0;
      discardLine = false;
    } else if (!discardLine) {
      if (inputLength < sizeof(inputLine) - 1) {
        inputLine[inputLength++] = c;
      } else {
        // 긴 입력을 명령 일부로 해석하지 않고 줄 끝까지 버린다.
        inputLength = 0;
        discardLine = true;
        armed = false;
        stopMotors();
        Serial.println(F("LINE_TOO_LONG,PWM_ZERO"));
      }
    }
  }
}
