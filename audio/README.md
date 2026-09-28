# DFPlayer Pro DFR0768 음원 준비

실제로 구매한 모듈은 [DFPlayer Pro DFR0768](https://www.devicemart.co.kr/goods/view?no=13903819)입니다.
**microSD 카드 슬롯이 없고 128 MB 내장 저장공간을 USB-C로 사용합니다.**
[`mp3/0001.mp3`](mp3/0001.mp3)은 약 1.2초짜리 스피커 시험음입니다.
실제 구조 안내 음성으로 바꿀 때는 현재 DFPlayer Pro에 복사된 파일 이름인
`bbibip.mp3`으로 맞추세요. Arduino 펌웨어는 `/bbibip.mp3`을 재생합니다.

1. 로봇 메인 전원을 끕니다. 모듈의 USB-C 단자와 Ubuntu 노트북을 **데이터 전송이 되는 USB 케이블**로 연결합니다. Nano Every의 USB 단자가 아닌 **DFPlayer Pro의 USB-C 단자**에 꽂습니다.
2. Ubuntu 파일 앱에 나타난 새 USB 저장장치를 엽니다. 보이는 파일은 먼저 확인하고, 저장장치를 포맷하지 마세요.
3. `bbibip.mp3`을 저장장치 **최상위**에 복사합니다. 모듈 안에서는 `/bbibip.mp3` 경로가 됩니다. 2026-09-28 Windows에서 실제 파일을 이 이름으로 복사했습니다. 저장소의 [`mp3/0001.mp3`](mp3/0001.mp3)은 별도의 짧은 시험음입니다.
4. 파일 앱에서 저장장치를 **꺼내기** 한 뒤 USB-C 케이블을 뽑습니다. 모듈 USB-C가 안쪽이라 연결할 수 없다면 분해하거나 전원을 켠 채 케이블을 억지로 꽂지 말고 다른 접근 방법을 정합니다.
5. Nano Every에 **DFPlayer Pro용으로 수정된** `firmware/arduino/rescue_beacon_firmware/rescue_beacon_firmware.ino`를 업로드합니다. 이전에 업로드한 Mini용 펌웨어는 Pro의 명령을 보낼 수 없습니다. 모터 주행 프로세스를 종료하고 업로드 중 바퀴가 움직일 수 없도록 준비합니다. [업로드 순서](../firmware/arduino/README.md#빌드와-업로드)를 따릅니다.
6. 업로드 뒤 다른 시리얼 프로그램이 모두 종료된 상태에서 RDK 터미널에 입력합니다.

   ```bash
   cd ~/rescue_ws/rescue-beacon-robot
   python3 scripts/arduino_smoke_test.py --port /dev/ttyACM0 --beep
   ```

`ACK,BEEP`는 Arduino가 UART로 재생 명령을 보냈다는 뜻입니다. 스피커에서 실제 소리가 나는지도 확인해야 합니다. 재생 시험 중 바퀴가 움직이면 메인 전원을 즉시 끕니다.

DFPlayer Pro의 USB 파일 복사와 115200 baud AT 명령은 [DFRobot 예제](https://wiki.dfrobot.com/dfr0768/docs/20423)와 [명령 참고서](https://wiki.dfrobot.com/dfr0768/docs/20422)를 따릅니다. 회로도에는 이전 가정인 DFPlayer Mini 심벌이 남아 있어 실제 배선은 Pro 핀 이름으로 다시 확인해야 합니다.
