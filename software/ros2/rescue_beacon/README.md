# Rescue Beacon ROS 2 패키지

RDK X5에서 아래 네 노드가 동작합니다.

```text
/scan ── lidar_nav_node ── /search_cmd_vel ──┐
                                             ├─ mission_controller_node ── /cmd_vel
/rescue_yolo_detections ── person_follow_node ┤                └─ /beacon_trigger
                         └─ /person_cmd_vel ┘
                                                      serial_bridge_node
                                                      └─ Nano Every USB
```

`mission_controller_node`가 최종 `/cmd_vel`의 유일한 정상 퍼블리셔입니다.
상태는 `SEARCH → CONFIRM → APPROACH → ALERT`이며, ALERT는 노드를
재시작할 때까지 유지됩니다. 사람 탐지 입력과 LiDAR 스캔이 오래되거나
유효하지 않으면 정지합니다. 탐색·추적 입력과 시리얼 명령에도 각각
시간 초과 처리가 있습니다.

## 실행 인자

`bash scripts/run_mission.sh`는 저장소 최상위 경로에서 실행합니다.

| 인자 | 기본값 | 의미 |
| --- | --- | --- |
| `enable_person` | `true` | 사람 추적 노드 실행 |
| `enable_serial` | `false` | Arduino USB 연결 |
| `enable_motion` | `false` | 시리얼 브리지가 0 이외의 모터 명령 전달 |
| `serial_port` | `/dev/ttyACM0` | Arduino 포트 |

`enable_motion:=true`는 `enable_serial:=true`와 함께 사용합니다.
시리얼 브리지는 `READY,1` 응답을 받은 뒤에만 `CMD`와 `BEEP`를
보냅니다. 다른 스케치가 설치된 보드에는 모터 명령을 보내지 않습니다.
`/beacon_trigger`는 ALERT 상태를 반복 발행하고, 브리지는 상승 시
한 번만 재생 요청을 보냅니다. 연결이 끊겼다가 복구되면 ALERT 재생을
다시 요청합니다.

## 토픽

| 토픽 | 타입 | 의미 |
| --- | --- | --- |
| `/scan` | `sensor_msgs/msg/LaserScan` | LiDAR 입력 |
| `/rescue_yolo_detections` | `ai_msgs/msg/PerceptionTargets` | YOLO 사람 상자 |
| `/search_cmd_vel` | `geometry_msgs/msg/Twist` | LiDAR 탐색 후보 |
| `/person_cmd_vel` | `geometry_msgs/msg/Twist` | 사람 접근 후보 |
| `/person_detected`, `/person_close` | `std_msgs/msg/Bool` | 탐지와 근접 프록시 |
| `/mission_state` | `std_msgs/msg/String` | 상태 머신 |
| `/cmd_vel` | `geometry_msgs/msg/Twist` | 최종 주행 명령 |
| `/beacon_trigger` | `std_msgs/msg/Bool` | 음향 안내 상태 |
| `/arduino_ready` | `std_msgs/msg/Bool` | 호환 펌웨어 통신 여부 |
| `/arduino_telemetry` | `std_msgs/msg/String` | ENC/ACK/ERR 직렬 메시지 |
| `/sound_detected` | `std_msgs/msg/Bool` | LM393 디지털 입력 |

사람 상자의 높이 비율로 접근을 멈추므로 실제 거리 센서는 아닙니다.
단일 LM393의 소리 입력은 모니터링만 하며 방향 탐색에는 쓰지 않습니다.
하드웨어별 실행 순서는
[대회 실행 안내](../../../docs/competition-runbook.md)에 있습니다.
