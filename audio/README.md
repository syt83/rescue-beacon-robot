# DFPlayer Pro DFR0768 음원 준비

실제로 구매한 모듈은 [DFPlayer Pro DFR0768](https://www.devicemart.co.kr/goods/view?no=13903819)입니다.
**microSD 카드 슬롯이 없고 128 MB 내장 저장공간을 USB-C로 사용합니다.**
[`mp3/0001.mp3`](mp3/0001.mp3)은 약 1.2초짜리 스피커 시험음입니다.
현재 DFPlayer Pro에 복사된 첫 번째 파일은 `bbibip.mp3`입니다. 실물에서
첫 번째 파일 재생 명령으로 이 소리가 나는 것을 확인했습니다.

1. 로봇 메인 전원을 끄고 DFPlayer Pro의 USB-C 단자를 데이터 케이블로 컴퓨터에 연결합니다. Nano Every의 USB 단자가 아닙니다.
2. Windows에서 열린 DFPlayer Pro USB 드라이브의 최상위에 `bbibip.mp3`을 복사합니다. 실제 장비에서는 Windows로 복사를 마쳤습니다. 파일이 여럿이면 첫 번째 파일 번호는 복사 순서에 따라 달라질 수 있으므로 재생 시험으로 확인하세요.
3. 드라이브를 안전하게 꺼낸 뒤 USB-C 케이블을 뽑습니다. Nano에 DFPlayer Pro용 펌웨어가 없다면 [업로드 순서](../firmware/arduino/README.md#빌드와-업로드)를 따릅니다.
4. 다른 시리얼 프로그램을 종료하고 RDK 터미널에 입력합니다.

   ```bash
   cd ~/rescue_ws/rescue-beacon-robot
   python3 scripts/arduino_smoke_test.py --port /dev/ttyACM0 --first-track
   ```

`ACK,BEEP2`는 Arduino가 UART로 첫 번째 파일 재생 명령을 보냈다는 뜻입니다. 스피커에서 실제 소리가 나는지도 확인해야 합니다. 재생 시험 중 바퀴가 움직이면 메인 전원을 즉시 끕니다.

처음 앰프는 뜨거워져 교체했습니다. 교체한 앰프에서는 `PLAY` 버튼으로
“music” 안내음이 들렸고, `--first-track` 시험에서는 원하는 `bbibip.mp3`이
실제로 들렸습니다. `--beep`가 보내는 경로 지정 명령은 이 장비에서 소리를
내지 않았습니다. 따라서 ROS 안내는 검증된 `BEEP,2` → `AT+PLAYNUM=1`을
사용합니다. 현재 Arduino 펌웨어 볼륨 기본값은 20입니다. 다른 파일을
추가하거나 지우면 첫 번째 파일이 바뀔 수 있으므로 다시 들어 보고 확인하세요.

DFPlayer Pro의 USB 파일 복사와 115200 baud AT 명령은 [DFRobot 예제](https://wiki.dfrobot.com/dfr0768/docs/20423)와 [명령 참고서](https://wiki.dfrobot.com/dfr0768/docs/20422)를 따릅니다. 회로도에는 이전 가정인 DFPlayer Mini 심벌이 남아 있어 실제 배선은 Pro 핀 이름으로 다시 확인해야 합니다.
