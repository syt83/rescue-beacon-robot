# LiDAR 없이 카메라 사람 접근 시험

이 시험은 X4 Pro가 거리 0만 보고할 때 사용하는 **2초짜리 저속 시험**이다.
YOLO가 사람을 탐지하면 로봇이 그 상자 쪽으로 향한다. 현재 모델은 누운 자세를
별도로 판정하지 않으므로, **화면에는 누운 사람 한 명만** 들어오게 한다.
모터는 초속 0.05m, 회전 초속 0.20rad 이하로 제한한다. 정상 종료와
`ALERT`에서는 약 0.5초 동안 속도를 줄이고, 통신이 끊기면 즉시 정지한다.
음원은 재생하지 않는다.

LiDAR 장애물 감지는 이 모드에서 사용하지 않는다. 경로에 물건이 없고,
로봇과 사람 사이가 1~2m일 때만 시험한다. 다른 한 명이 화면 밖에서
메인 스위치를 바로 끌 수 있어야 한다. 배터리가 뜨겁거나 부풀었거나
이상한 냄새가 나면 실행하지 않는다.

RDK 터미널을 다음 순서로 연다. LiDAR 터미널과 기존 미션 터미널은 종료한다.

| 터미널 | 실행 명령 |
| --- | --- |
| 1 카메라 | `cd ~/rescue_ws/rescue-beacon-robot && bash scripts/run_camera.sh` |
| 2 YOLO | `cd ~/rescue_ws/rescue-beacon-robot && bash scripts/run_yolo.sh` |
| 3 영상 | `cd ~/rescue_ws/rescue-beacon-robot && bash scripts/run_yolo_monitor.sh --host 0.0.0.0` |
| 4 시험 | `cd ~/rescue_ws/rescue-beacon-robot && python3 scripts/run_camera_only_trial.py` |

노트북 브라우저에서 `http://<RDK_IP>:8088`을 열고, 누운 사람에게 초록색
사람 상자가 표시되는지 먼저 확인한다. 터미널 4에서 주의사항을 읽고 `RUN`을
입력하면 Arduino `READY,1` 확인 후 최대 2초 동안만 접근한다. 종료되면
두 바퀴가 실제로 멈췄는지 눈으로 확인한다. `Ctrl+C`나 메인 스위치로도
즉시 중단할 수 있다. 바퀴가 계속 돌면 메인 스위치를 끈다.

상자 높이가 화면의 72% 또는 폭이 65%가 되면 `ALERT`로 전환해 정지한다.
화면 점유율은 실제 거리가 아니다. 이 시험이 움직임과 정지를 확인해도
사람 앞에서 정확한 거리로 멈추는 기능은 검증되지 않는다.
