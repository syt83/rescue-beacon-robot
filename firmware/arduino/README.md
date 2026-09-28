# Arduino Nano Every 펌웨어

## 모터 전원 없이 엔코더 확인

[sensor_only_diagnostic.ino](sensor_only_diagnostic/sensor_only_diagnostic.ino)는
모터 명령을 받지 않고 왼쪽·오른쪽 엔코더의 카운트와 A/B 핀 상태를 보여줍니다.
노트북에 연결한 Nano Every에서만 실행하며, **메인 스위치는 끈 상태로**
유지합니다. 모터 전원과 RDK 전원이 같은 스위치에 묶여 있으므로 RDK에서
실행하는 시험은 아직 진행하지 않습니다.

1. 메인 스위치를 끄고 Nano USB를 Ubuntu 노트북에 연결합니다.
2. Arduino IDE에서 위 파일을 열어 **Arduino Nano Every** 보드와 Nano의
   포트를 선택한 뒤 업로드합니다.
3. 시리얼 모니터를 **115200 baud**로 엽니다. `SENSOR_ONLY_READY` 다음에
   `ENC,<왼쪽>,<오른쪽>,PINS,<LA>,<LB>,<RA>,<RB>,SOUND,<0/1>`이
   반복해서 나오는지 확인합니다.
4. 메인 스위치를 **켜지 않고**, 손으로 왼쪽 바퀴만 천천히 한 바퀴 돌려
   첫 번째 카운트가 변하는지 봅니다. 이어 오른쪽 바퀴만 돌려 두 번째
   카운트가 변하는지 봅니다. 카운트가 증가하는지 감소하는지는 방향에
   따라 달라질 수 있습니다.

카운트가 0에서 바뀌지 않으면 `PINS` 값도 함께 기록합니다. Nano USB만으로
엔코더에 전원이 공급되지 않는 배선일 수 있으므로, 이 결과만으로 엔코더
고장을 판정하지 않습니다. `SOUND`는 회로도의 Arduino_Core 그림에 D10
연결이 표시되지 않아 현재 배선 확인 전에는 참고값일 뿐입니다.

## 모터만 확인하는 임시 스케치

[motor_only_diagnostic.ino](motor_only_diagnostic/motor_only_diagnostic.ino)는
카메라·ROS·RDK 명령 없이 Nano Every에서 MD20A 두 개만 시험합니다.
이전 시험에서 속도 0 명령에도 바퀴가 계속 돌았으므로 **아래 순서 외의 주행
명령은 실행하지 마세요.** 스케치는 부팅 시 PWM을 0으로 설정하지만, 실제
배선이나 드라이버 문제로 바퀴가 도는 것은 소프트웨어가 막지 못합니다.

1. **메인 스위치를 끈 상태에서** Nano USB를 RDK에서 빼서 Ubuntu 노트북에
   연결합니다. Arduino IDE에서 위 `.ino` 파일을 열고 보드를
   **Arduino Nano Every**, 포트를 Nano USB 장치로 선택해 업로드합니다.
   보드가 목록에 없다면 Boards Manager에서 **Arduino megaAVR Boards**를
   설치합니다. 업로드 중에도 메인 스위치는 끈 채 둡니다.
2. Arduino IDE의 시리얼 모니터를 **115200 baud**, 줄 끝은 **Newline**으로
   설정합니다. `STATUS`를 보내 `STATUS,IDLE`이 오는지 확인합니다.
   이때 노트북 USB가 Nano만 켜고 모터 배터리는 꺼진 상태입니다.
3. 차체를 받침대에 고정해 두 바퀴를 띄우고, 손은 바퀴에서 떼고 메인
   스위치에 바로 닿을 수 있게 합니다. 메인 스위치를 켠 뒤 **아무 명령도
   보내지 않고** 확인합니다. 바퀴가 하나라도 돌면 즉시 메인 스위치를
   끄고 더 진행하지 않습니다.
4. 두 바퀴가 가만히 있을 때만 `ARM`을 보내고 5초 안에 `LEFT`를 보냅니다.
   왼쪽만 0.2초 돌고 멈추는지 봅니다. 계속 돌면 메인 스위치를 즉시 끕니다.
   정상이면 다시 `ARM` 다음 `RIGHT`를 보내 오른쪽을 확인합니다.
   `STOP`은 PWM 0 명령이지만, 실제 정지는 눈으로 확인해야 합니다.
5. 시험을 마치면 메인 스위치를 끕니다. 이 임시 스케치는 ROS용
   `READY,1` 프로토콜을 제공하지 않으므로 대회 코드를 쓰려면 아래의
   `rescue_beacon_firmware.ino`를 다시 업로드해야 합니다.

시리얼 모니터에서 보낼 명령은 다음과 같습니다. 한 줄씩 전송합니다.

```text
STATUS
ARM
LEFT
ARM
RIGHT
STOP
```

`ARM`은 다음 한 번의 구동만 허용하고 5초 뒤 만료됩니다. `LEFT`와
`RIGHT`는 PWM 60/255로 최대 0.2초만 구동합니다. 출력 메시지
`PWM_ZERO_COMMAND`는 Arduino가 0을 **명령했다**는 뜻이며, 바퀴가 실제로
멈췄다는 측정값은 아닙니다.

## 구조 로봇 본 펌웨어

`rescue_beacon_firmware/rescue_beacon_firmware.ino`는 RDK X5와 USB 직렬
통신을 하고 Cytron MD20A 2개, 엔코더, LM393, **DFPlayer Pro DFR0768**을 제어합니다.
실제 구매 모듈은 Pro이며, 이전 Mini용 9600 baud 바이너리 명령을
115200 baud AT 명령으로 수정했습니다. 수정한 펌웨어는 다시 업로드해야 합니다.

## 회로도 기준 핀 배치

아래 표는 `hardware/kicad/rescue-beacon-robot.kicad_sch`의
`Arduino_Core` 회로도와 사용자가 공유한 회로도 그림 기준입니다.
실제 배선이 다르면 스케치 맨 위의 핀 상수와 모터 반전 값을 수정한 뒤
업로드하세요.

| Nano Every | 연결 대상 | 코드 상수 |
| --- | --- | --- |
| D3 (PWM) | 왼쪽 MD20A PWM (`PWM_L`) | `LEFT_PWM_PIN` |
| D4 | 왼쪽 MD20A DIR (`DIR_L`) | `LEFT_DIR_PIN` |
| D9 (PWM) | 오른쪽 MD20A PWM (`PWM_R`) | `RIGHT_PWM_PIN` |
| D7 | 오른쪽 MD20A DIR (`DIR_R`) | `RIGHT_DIR_PIN` |
| D2 / D5 | 왼쪽 엔코더 A / B | `LEFT_ENC_A_PIN` / `LEFT_ENC_B_PIN` |
| D6 / D8 | 오른쪽 엔코더 A / B | `RIGHT_ENC_A_PIN` / `RIGHT_ENC_B_PIN` |
| D10 | LM393 DO용 코드 핀; 제공된 `Arduino_Core` 그림에는 연결 표시 없음 | `SOUND_PIN` |
| TX (D1) | DFPlayer Pro RX | `Serial1` |
| RX (D0) | DFPlayer Pro TX (선택, 현재 응답 미사용) | `Serial1` |
| USB | RDK X5 | `Serial`, 115200 baud |

Arduino와 MD20A 2개, DFPlayer Pro, LM393의 **GND는 공통**으로 연결합니다.
LM393 신호선이 D10에 연결되지 않았다면 `SOUND` 값은 실제 소리 상태를
나타내지 않습니다. 음향 감지 시험 전에 이 신호선을 확인하세요.
MD20A의 모터 전원과 모터는 제품 사양에 맞춰 별도로 연결하세요.
모터 전원선을 Nano의 5V 핀에 연결하지 마세요. DFPlayer Pro와 PAM8403은
적합한 안정된 전원을 사용하세요. PAM8403 입력은 DFPlayer Pro의
DAC 출력(DACL/DACR)에 연결하고, Pro의 L+/L- 또는 R+/R- 스피커 출력을
앰프 입력에 연결하지 마세요. 기존 KiCad의 Mini 심벌은 실제 Pro의
핀 배치를 나타내지 않으므로 실물 핀 이름을 기준으로 확인합니다.

Nano Every 핀 기능은 [Arduino 핀도](https://docs.arduino.cc/resources/pinouts/ABX00028-full-pinout.pdf),
PWM/DIR와 자체 테스트 버튼은 [Cytron MD20A 안내](https://www.cytron.io/p-20amp-6v-30v-dc-motor-driver),
DFPlayer Pro 전원·UART·DAC는 [DFRobot 안내](https://wiki.dfrobot.com/dfr0768/)를
기준으로 확인했습니다.

## 음원

USB-C로 Pro 내장 저장공간의 최상위에 `bbibip.mp3`을 넣습니다. 스케치는
`AT+PLAYFILE=/bbibip.mp3`을 보냅니다. [음원 복사 순서](../../audio/README.md)를
따르세요. Nano Every의 USB 포트로는 Pro에 파일을 복사할 수 없습니다.
`ACK,BEEP`는 Arduino가 재생 명령을 전달했다는 뜻이며, 실제 소리가
났는지는 귀로 확인해야 합니다.

## 빌드와 업로드

RDK X5에는 [Arduino CLI](https://arduino.github.io/arduino-cli/latest/installation/)
1.5.1과 `arduino:megaavr` 코어 1.8.8을 `~/rescue_ws` 아래에 설치했습니다.
저장소 최상위 경로에서 다음을 실행하세요. 노트북의 Arduino IDE에서
업로드하려면 보드를 **Arduino Nano Every**로 선택하고 보드를 노트북 USB에
연결해야 합니다.
ROS 시리얼 브리지와 시리얼 모니터는 먼저 종료합니다.
이전 Mini용 스케치는 Nano Every 대상 빌드와 실물 업로드를 통과했습니다.
Pro용 변경본은 다시 빌드·업로드한 뒤 소리를 실물로 확인해야 합니다.

```bash
~/rescue_ws/bin/arduino-cli compile --fqbn arduino:megaavr:nona4809 firmware/arduino/rescue_beacon_firmware
~/rescue_ws/bin/arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:megaavr:nona4809 firmware/arduino/rescue_beacon_firmware
```

업로드에서 `jtagmkII_getsync(): sign-on command: status -1`가 반복되면,
Nano Every의 USB 포트를 1200 baud로 열었다 닫아 업로드 모드로 전환한 뒤
바로 업로드 명령을 재시도하세요. 이 장비에서는 그 순서로 성공했습니다.

```bash
python3 -c 'import serial,time; s=serial.Serial("/dev/ttyACM0",1200,timeout=0.1); time.sleep(0.3); s.close()'
~/rescue_ws/bin/arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:megaavr:nona4809 firmware/arduino/rescue_beacon_firmware
```

현재 이 장비의 Nano Every는 `/dev/ttyACM0`이고 LiDAR는 `/dev/ttyUSB0`입니다.
다른 장비에서는 `ls -l /dev/serial/by-id/`로 포트를 다시 찾으세요.
업로드 후 모터 전원을 끈 상태에서:

```bash
python3 scripts/arduino_smoke_test.py --port /dev/ttyACM0
```

`READY,1`, `ENC,...`, `SOUND,...`가 나와야 합니다. 2026-09-27에 업로드 후
`READY,1`, `ENC,0,0`, `SOUND,0`을 확인했습니다. 이전 스케치의
`Nano Every Ready` 출력이 보이면 업로드가 완료되지 않은 상태입니다.

## 직렬 프로토콜과 안전 동작

| 방향 | 메시지 | 의미 |
| --- | --- | --- |
| RDK → Nano | `HELLO` | 펌웨어 버전 요청 |
| Nano → RDK | `READY,1` | 호환 프로토콜 응답 |
| RDK → Nano | `CMD,<m/s>,<rad/s>` | 차동 구동 명령 |
| RDK → Nano | `BEEP,1` | Pro 내장 저장공간의 `/bbibip.mp3` 재생 요청 |
| Nano → RDK | `ENC,<left>,<right>` | 엔코더 누적 카운트 |
| Nano → RDK | `SOUND,<0/1>` | LM393 디지털 입력 |
| Nano → RDK | `ACK,BEEP` / `ERR,CMD` | 명령 접수 / 잘못된 주행 명령 |

부팅 시 PWM은 0입니다. 유효한 `CMD`가 0.5초 동안 오지 않으면 PWM을 0으로
만듭니다. 명령 크기가 상한을 넘거나 형식이 틀리면 정지합니다.
이는 소프트웨어 정지 장치이며 실제 시험에서는 모터 전원 차단 수단도
준비해야 합니다.
2026-09-27 신호 GND 선을 재연결한 뒤 바퀴가 속도 0 명령에도 계속 돌아
메인 스위치로 정지했습니다. 이후 사용자가 배선을 다시 하고 양쪽 모터의
직선·곡선·회전 주행과 엔코더 동작을 확인했습니다. ROS 브리지의 1회
전진 명령으로도 양쪽 바퀴가 잠깐 돌고 멈췄습니다. ROS 회전·자율 주행은
아직 시험하지 않았습니다. 배선 오류나 접촉 불량에는
소프트웨어 정지 명령이 통하지 않을 수 있으므로 물리 전원 스위치를
사용할 수 있게 둡니다.
