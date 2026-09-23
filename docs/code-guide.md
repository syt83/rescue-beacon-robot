# 코드 안내

GitHub의 **Code** 탭에서 아래 링크를 누르면 소스 코드를 바로 볼 수 있습니다.
각 파일에는 주요 판단과 안전 동작을 설명하는 한국어 주석을 넣었습니다.
실행 명령과 터미널 순서는 [대회 실행 안내](competition-runbook.md)에 있습니다.

## 먼저 읽을 파일

| 순서 | 파일 | 역할 |
| --- | --- | --- |
| 1 | [실행 설정](../software/ros2/rescue_beacon/config/rescue_beacon.yaml) | 속도, 정지 거리, 토픽, 시간 초과 값 |
| 2 | [미션 제어](../software/ros2/rescue_beacon/rescue_beacon/mission_controller_node.py) | SEARCH → CONFIRM → APPROACH → ALERT, 최종 `/cmd_vel`과 안전 정지 |
| 3 | [사람 추적](../software/ros2/rescue_beacon/rescue_beacon/person_follow_node.py) | YOLO 사람 상자로 회전·접근 명령 계산 |
| 4 | [LiDAR 탐색](../software/ros2/rescue_beacon/rescue_beacon/lidar_nav_node.py) | 장애물 거리를 보고 탐색 명령 계산 |
| 5 | [YOLO 연결](../software/perception/ros_yolo_bridge.py) | 기존 YOLO의 상자를 ROS 메시지로 변환 |
| 6 | [Arduino 연결](../software/ros2/rescue_beacon/rescue_beacon/serial_bridge_node.py) | USB 통신, 펌웨어 확인, 모터·음향 명령 전달 |
| 7 | [Nano Every 펌웨어](../firmware/arduino/rescue_beacon_firmware/rescue_beacon_firmware.ino) | 모터 PWM, 엔코더, 소리 센서, DFPlayer Mini 제어 |

## 데이터가 흐르는 순서

```text
카메라 → 기존 YOLO → ros_yolo_bridge → person_follow_node ─┐
                                                       ├→ mission_controller_node → /cmd_vel
LiDAR → /scan → lidar_nav_node ──────────────────────────┘            │
                                                                      ├→ /beacon_trigger
                                                                      ↓
                                                   serial_bridge_node → Nano Every
```

`mission_controller_node`만 최종 `/cmd_vel`을 발행합니다. Arduino로 주행 명령을
전달하려면 시리얼 연결과 모터 전달을 각각 켜야 합니다. 기본값은 둘 다 꺼져
있습니다. `ALERT`에 도달하면 정지 상태를 유지하며, 새 탐색은 미션 노드를
재시작해야 시작됩니다.

## 실행과 확인 코드

| 파일 | 용도 |
| --- | --- |
| [ROS 시작 설정](../software/ros2/rescue_beacon/launch/rescue_beacon.launch.py) | 노드를 한 번에 실행하고 Arduino 연결 여부를 선택 |
| [빌드](../scripts/build_ros.sh) | ROS 패키지 빌드 |
| [카메라](../scripts/run_camera.sh) · [YOLO](../scripts/run_yolo.sh) · [LiDAR](../scripts/run_lidar.sh) · [미션](../scripts/run_mission.sh) | 터미널별 실행 명령 |
| [시리얼 단독 실행](../scripts/run_serial_bridge.sh) | Arduino 통신 점검 |
| [Arduino USB 점검](../scripts/arduino_smoke_test.py) | `READY,1`, 엔코더, 소리 입력 확인; 모터에는 0 명령만 전송 |
| [미션 안전 테스트](../software/ros2/rescue_beacon/test/test_mission_safety.py) · [시리얼 테스트](../software/ros2/rescue_beacon/test/test_serial_bridge.py) | 상태 고정, 센서 시간 초과, 펌웨어 확인 등의 자동 테스트 |

기존 `ros_yolo_live.py` 런타임과 `best_bayese_640x640_nv12.bin` 모델은
RDK의 `~/rdk_model_zoo`와 홈 디렉터리에 있습니다. 이 저장소에는 YOLO를 ROS에
연결하는 코드만 들어 있습니다. [YOLO 연결 설명](../software/perception/README.md)을
참고하세요. Arduino 배선 전에는 [펌웨어 핀 안내](../firmware/arduino/README.md)를
확인하세요.
