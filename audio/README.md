# DFPlayer Mini 음원 준비

[`mp3/0001.mp3`](mp3/0001.mp3)은 스피커 시험용 1.2초 짧은 소리입니다.
구조 안내 음성으로 바꿀 때도 카드의 파일 경로는 `/mp3/0001.mp3`입니다.
현재 Arduino 펌웨어는 DFPlayer Mini의 해당 번호를 재생하도록 설정돼 있습니다.

1. 로봇 메인 전원을 끄고 DFPlayer Mini에서 **소리 재생용 microSD**를 뺍니다.
2. microSD를 카드 리더기에 넣고 Ubuntu 노트북에 연결합니다. 리더기의
   USB-C 단자를 사용해도 됩니다. Arduino의 USB 단자는 음원 전송에 쓰지
   않습니다.
3. 카드가 FAT32인지 확인하고, 카드의 최상위 위치에 `mp3` 폴더를 만듭니다.
   이 저장소의 `audio/mp3/0001.mp3`을 그 폴더에 복사합니다.
4. Ubuntu 파일 관리자에서 카드를 **꺼내기** 한 뒤 리더기에서 빼고,
   로봇 전원이 꺼진 상태에서 DFPlayer Mini에 다시 꽂습니다.
5. 로봇 전원을 켜고 ROS 미션·시리얼 브리지가 종료된 상태에서 RDK 터미널에
   아래 명령을 입력합니다.

   ```bash
   cd ~/rescue_ws/rescue-beacon-robot
   python3 scripts/arduino_smoke_test.py --port /dev/ttyACM0 --beep
   ```

`ACK,BEEP`는 Arduino가 재생 명령을 보냈다는 뜻입니다. 스피커에서 실제
소리가 들리는지도 확인해야 합니다. 재생 중 바퀴가 움직이면 메인 전원을
즉시 끄고 배선을 확인합니다.

음악 모듈 **자체**에 USB-C 단자가 있다면 DFPlayer Pro 등 다른 모델일 수
있습니다. 현재 펌웨어는 DFPlayer Mini용이므로 모델을 확인한 뒤 진행합니다.
DFPlayer Mini의 파일 경로와 카드 형식은
[DFRobot 안내](https://wiki.dfrobot.com/dfr0299/docs/20905)를 따릅니다.
