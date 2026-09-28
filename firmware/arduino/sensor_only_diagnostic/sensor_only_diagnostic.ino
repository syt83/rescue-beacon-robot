/*
  Nano Every 센서 전용 진단: 엔코더와 소리 센서 입력만 읽는다.

  시리얼 모니터: 115200 baud. 250 ms마다 다음 형식으로 출력한다.
    ENC,<left_count>,<right_count>,PINS,<LA>,<LB>,<RA>,<RB>,SOUND,<0_or_1>

  모터 PWM/DIR 핀은 부팅 시 LOW로 설정하고 이후 절대 구동하지 않는다.
  단, 배선이나 드라이버가 잘못되면 소프트웨어로 모터 정지를 보장할 수 없다.
  모터 전원이 꺼진 상태에서 노트북 USB로 Nano를 켜고 손으로 바퀴를 돌린다.
  USB만으로 엔코더에 전원이 공급되지 않으면 카운트가 변하지 않을 수 있다.
*/

#include <Arduino.h>

// 회로도 Arduino_Core: 왼쪽 MD20A PWM/DIR=D3/D4, 오른쪽=D9/D7.
const uint8_t LEFT_PWM_PIN = 3;
const uint8_t LEFT_DIR_PIN = 4;
const uint8_t RIGHT_PWM_PIN = 9;
const uint8_t RIGHT_DIR_PIN = 7;

// 회로도 Arduino_Core: 엔코더 A/B 왼쪽=D2/D5, 오른쪽=D6/D8.
const uint8_t LEFT_ENC_A_PIN = 2;
const uint8_t LEFT_ENC_B_PIN = 5;
const uint8_t RIGHT_ENC_A_PIN = 6;
const uint8_t RIGHT_ENC_B_PIN = 8;

// 본 펌웨어의 LM393 입력. Arduino_Core 그림에는 D10 연결이 보이지 않는다.
const uint8_t SOUND_PIN = 10;
const bool SOUND_ACTIVE_LOW = true;

volatile long leftCount = 0;
volatile long rightCount = 0;
unsigned long lastReportMs = 0;

void leftEncoderISR() {
  leftCount += digitalRead(LEFT_ENC_B_PIN) ? 1 : -1;
}

void rightEncoderISR() {
  rightCount += digitalRead(RIGHT_ENC_B_PIN) ? 1 : -1;
}

void setup() {
  // 출력 모드가 되기 전에 LOW를 래치한다. 이후 PWM을 켜는 코드가 없다.
  digitalWrite(LEFT_PWM_PIN, LOW);
  digitalWrite(RIGHT_PWM_PIN, LOW);
  digitalWrite(LEFT_DIR_PIN, LOW);
  digitalWrite(RIGHT_DIR_PIN, LOW);
  pinMode(LEFT_PWM_PIN, OUTPUT);
  pinMode(RIGHT_PWM_PIN, OUTPUT);
  pinMode(LEFT_DIR_PIN, OUTPUT);
  pinMode(RIGHT_DIR_PIN, OUTPUT);

  pinMode(LEFT_ENC_A_PIN, INPUT_PULLUP);
  pinMode(LEFT_ENC_B_PIN, INPUT_PULLUP);
  pinMode(RIGHT_ENC_A_PIN, INPUT_PULLUP);
  pinMode(RIGHT_ENC_B_PIN, INPUT_PULLUP);
  pinMode(SOUND_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(LEFT_ENC_A_PIN), leftEncoderISR, CHANGE);
  attachInterrupt(digitalPinToInterrupt(RIGHT_ENC_A_PIN), rightEncoderISR, CHANGE);

  Serial.begin(115200);
  Serial.println(F("SENSOR_ONLY_READY; MOTOR_COMMANDS_DISABLED"));
}

void loop() {
  if (millis() - lastReportMs < 250) return;
  lastReportMs = millis();

  // 8비트 MCU에서 32비트 카운터가 중간에 바뀌지 않도록 원자적으로 복사한다.
  noInterrupts();
  long left = leftCount;
  long right = rightCount;
  interrupts();

  Serial.print(F("ENC,"));
  Serial.print(left);
  Serial.print(',');
  Serial.print(right);
  Serial.print(F(",PINS,"));
  Serial.print(digitalRead(LEFT_ENC_A_PIN));
  Serial.print(',');
  Serial.print(digitalRead(LEFT_ENC_B_PIN));
  Serial.print(',');
  Serial.print(digitalRead(RIGHT_ENC_A_PIN));
  Serial.print(',');
  Serial.print(digitalRead(RIGHT_ENC_B_PIN));
  Serial.print(F(",SOUND,"));
  Serial.println(digitalRead(SOUND_PIN) == (SOUND_ACTIVE_LOW ? LOW : HIGH) ? 1 : 0);
}
