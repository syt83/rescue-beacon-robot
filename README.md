# Rescue Beacon Robot

RDK X5, Arduino Nano Every, YDLIDAR X4 Pro, 카메라와 YOLO를 연결해 사람을
찾고 접근한 뒤 멈춰 음향 안내를 재생하는 대회용 ROS 2 프로젝트입니다.

## 현재 동작하는 범위

| 기능 | 상태 |
| --- | --- |
| 카메라 → YOLO → ROS 사람 탐지 | RDK X5에서 실측 완료 |
| LiDAR 탐색 명령, 사람 접근, SEARCH → CONFIRM → APPROACH → ALERT | ROS 실측 완료 |
| ALERT 이후 정지 유지, 센서/명령 시간 초과 시 정지 | ROS 실측 및 오프라인 점검 완료 |
| Nano Every USB 연결 | 장치 인식 완료 |
| Nano Every 펌웨어, 모터, 엔코더, LM393, DFPlayer Mini | Nano Every 대상 빌드 완료. 배선·업로드·실물 시험 필요 |

ROS 제어의 실제 이동 명령은 `mission_controller_node`가
`/cmd_vel`로 발행합니다. 시리얼은 기본적으로 **꺼져 있고**, 시리얼을 켜도
모터 전달은 기본적으로 **꺼져 있습니다**. `ALERT` 상태는 노드 재시작 전까지
유지됩니다.

## 구성

- RDK X5: ROS 2, 카메라, YOLO, LiDAR, 미션 제어
- Arduino Nano Every: PWM/DIR 모터 제어, 엔코더·LM393 입력, DFPlayer Mini 제어
- Cytron MDD10A + RB-35GM 엔코더 모터 2개
- DFPlayer Mini + PAM8403 + 스피커, microSD 카드

Arduino USB 프로토콜은 `HELLO`/`READY,1`로 펌웨어 버전을 확인합니다.
다른 스케치가 올라가 있으면 ROS 브리지는 모터 명령을 보내지 않습니다.
정확한 핀 제안과 업로드 방법은
[Arduino 펌웨어 안내](firmware/arduino/README.md)에 있습니다.

## 실행

1. [대회 실행 및 하드웨어 시험 순서](docs/competition-runbook.md)
2. [코드 전체 안내: 파일별 역할과 읽는 순서](docs/code-guide.md)
3. [ROS 패키지 구조와 토픽](software/ros2/rescue_beacon/README.md)
4. [YOLO 연결](software/perception/README.md)

이 장비의 YOLO 런타임과 `best_bayese_640x640_nv12.bin` 모델은 이 저장소 밖에
있습니다. 새 RDK에 복제할 때 두 파일을 따로 준비해야 합니다.

## 구현 범위

현재 거리 판단은 스테레오 깊이가 아니라 YOLO 사람 상자의 높이 비율을
사용합니다. LiDAR 탐색은 기본 장애물 회피이며 SLAM/경로 계획은 포함하지
않습니다. LM393 한 개는 소리 유무만 알 수 있으며 방향은 알 수 없습니다.
BNO085 자세 추정과 구조 대상 좌표 보고는 아직 구현되지 않았습니다.
실물 배선·핀 방향·음향 재생·바퀴 동작은 하드웨어 조립 후 검증해야 합니다.

## 라이선스

MIT
