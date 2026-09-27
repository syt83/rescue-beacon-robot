# Arduino Nano Every 펌웨어

`rescue_beacon_firmware/rescue_beacon_firmware.ino`는 RDK X5와 USB 직렬
통신을 하고 Cytron MDD10A, 엔코더, LM393, **DFPlayer Mini**를 제어합니다.
DFPlayer Pro의 AT 명령과는 호환되지 않습니다.

## 제안 핀 배치

아직 실제 배선이 없으므로 아래는 코드에 맞춘 **배선 제안**입니다. 실제 배선이
다르면 스케치 맨 위의 핀 상수와 모터 반전 값을 수정한 뒤 업로드하세요.

| Nano Every | 연결 대상 | 코드 상수 |
| --- | --- | --- |
| D5 (PWM) | MDD10A 채널 1 PWM | `LEFT_PWM_PIN` |
| D4 | MDD10A 채널 1 DIR | `LEFT_DIR_PIN` |
| D6 (PWM) | MDD10A 채널 2 PWM | `RIGHT_PWM_PIN` |
| D7 | MDD10A 채널 2 DIR | `RIGHT_DIR_PIN` |
| D2 / D8 | 왼쪽 엔코더 A / B | `LEFT_ENC_A_PIN` / `LEFT_ENC_B_PIN` |
| D3 / D9 | 오른쪽 엔코더 A / B | `RIGHT_ENC_A_PIN` / `RIGHT_ENC_B_PIN` |
| D10 | LM393 DO | `SOUND_PIN` |
| TX (D1) | DFPlayer Mini RX (1 kΩ 직렬 저항 권장) | `Serial1` |
| RX (D0) | DFPlayer Mini TX (선택, 현재 응답 미사용) | `Serial1` |
| USB | RDK X5 | `Serial`, 115200 baud |

Arduino와 MDD10A, DFPlayer Mini, LM393의 **GND는 공통**으로 연결합니다.
MDD10A의 모터 전원과 모터는 제품 사양에 맞춰 별도로 연결하세요.
모터 전원선을 Nano의 5V 핀에 연결하지 마세요. DFPlayer Mini와 PAM8403은
적합한 안정된 5V 전원을 사용하세요. PAM8403 입력은 DFPlayer Mini의 DAC
출력에 연결하고, DFPlayer의 SPK1/SPK2 출력을 앰프 입력에 연결하지 마세요.

Nano Every 핀 기능은 [Arduino 핀도](https://docs.arduino.cc/resources/pinouts/ABX00028-full-pinout.pdf),
PWM/DIR와 공통 GND는 [Cytron MDD10A 안내](https://sg.cytron.io/tutorial/mdd10a-maker-uno-dc-motor-control),
DFPlayer 전원·UART·DAC는 [DFRobot 안내](https://wiki.dfrobot.com/dfr0299)를
기준으로 확인했습니다.

## 음원

FAT32 microSD 카드에 `/mp3/0001.mp3`을 넣습니다. 스케치는 DFPlayer Mini의
`playMp3Folder(1)`에 해당하는 0x12 명령을 보냅니다.
`ACK,BEEP`는 Arduino가 재생 명령을 전달했다는 뜻이며, 실제 소리가
났는지는 귀로 확인해야 합니다.

## 빌드와 업로드

현재 RDK X5에는 `arduino-cli`가 기본 설치되어 있지 않습니다. Arduino IDE에서
보드를 **Arduino Nano Every**로 선택하고 스케치를 열어 업로드하거나,
[Arduino CLI](https://arduino.github.io/arduino-cli/latest/installation/)를
설치한 PC/RDK에서 저장소 최상위 경로 기준으로 다음을 실행하세요.
ROS 시리얼 브리지와 시리얼 모니터는 먼저 종료합니다.
이 스케치는 Arduino CLI 1.5.1, `arduino:megaavr` 코어 1.8.8로
Nano Every 대상 빌드를 통과했습니다.

```bash
arduino-cli core update-index
arduino-cli core install arduino:megaavr
arduino-cli compile --fqbn arduino:megaavr:nona4809 firmware/arduino/rescue_beacon_firmware
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:megaavr:nona4809 firmware/arduino/rescue_beacon_firmware
```

현재 이 장비의 Nano Every는 `/dev/ttyACM0`이고 LiDAR는 `/dev/ttyUSB0`입니다.
다른 장비에서는 `ls -l /dev/serial/by-id/`로 포트를 다시 찾으세요.
업로드 후 모터 전원을 끈 상태에서:

```bash
python3 scripts/arduino_smoke_test.py --port /dev/ttyACM0
```

`READY,1`, `ENC,...`, `SOUND,...`가 나와야 합니다. 지금 보드에서 보였던
`Nano Every Ready` / `WATCHDOG TIMEOUT -> MOTOR STOP`는 **다른 스케치**의
출력입니다. 이 저장소의 펌웨어를 업로드하기 전에는 ROS 브리지가
`READY,1`을 받지 못해 모터 명령을 보내지 않습니다.

## 직렬 프로토콜과 안전 동작

| 방향 | 메시지 | 의미 |
| --- | --- | --- |
| RDK → Nano | `HELLO` | 펌웨어 버전 요청 |
| Nano → RDK | `READY,1` | 호환 프로토콜 응답 |
| RDK → Nano | `CMD,<m/s>,<rad/s>` | 차동 구동 명령 |
| RDK → Nano | `BEEP,1` | `/mp3/0001.mp3` 재생 요청 |
| Nano → RDK | `ENC,<left>,<right>` | 엔코더 누적 카운트 |
| Nano → RDK | `SOUND,<0/1>` | LM393 디지털 입력 |
| Nano → RDK | `ACK,BEEP` / `ERR,CMD` | 명령 접수 / 잘못된 주행 명령 |

부팅 시 PWM은 0입니다. 유효한 `CMD`가 0.5초 동안 오지 않으면 PWM을 0으로
만듭니다. 명령 크기가 상한을 넘거나 형식이 틀리면 정지합니다.
이는 소프트웨어 정지 장치이며 실제 시험에서는 모터 전원 차단 수단도
준비해야 합니다.
