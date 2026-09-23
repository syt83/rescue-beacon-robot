# Rescue Beacon ROS2 Package

RDK X5에서 실행되는 Rescue Beacon Robot용 ROS2 패키지입니다.

현재는 YDLIDAR X4 Pro의 `/scan` 데이터를 이용한
기본 장애물 감지 및 회피 명령 생성 기능을 구현하고 있습니다.

## 현재 구현

```text
YDLIDAR X4 Pro
      ↓
    /scan
      ↓
 lidar_nav_node
      ↓
전방 / 좌측 / 우측 거리 판단
      ↓
   /cmd_vel
RDK X5에서 실행되는 구조 로봇용 ROS2 통합 제어 패키지입니다.

## MVP 파이프라인

```text
YDLIDAR X4 Pro ── /scan ──> lidar_nav_node ── /search_cmd_vel ──┐
                                                                │
RDK body detection ──> person_follow_node ── /person_cmd_vel ───┤
                                                                v
                                                   mission_controller_node
                                                                │
                                      /cmd_vel + /beacon_trigger
                                                                │
                                                        serial_bridge_node
                                                                │
                                                        Arduino Nano Every
                                                        ├─ MDD10A + motors
                                                        └─ DFPlayer Pro
```

상태 머신은 `SEARCH -> CONFIRM -> APPROACH -> ALERT` 순서입니다.

`mission_controller_node`가 최종 `/cmd_vel`의 유일한 퍼블리셔이며,
LiDAR 안전 정지 로직을 마지막 단계에서 적용합니다.

## 사람 탐지

`person_follow_node`는 D-Robotics의
`/hobot_mono2d_body_detection`
(`ai_msgs/msg/PerceptionTargets`)를 입력으로 사용합니다.

현재 접근 정지 판단은 **스테레오 미터 거리값이 아니라 바운딩박스 높이 비율을
근거리 프록시로 사용**합니다. 따라서 `stop_height_ratio`는 실제 카메라 장착 후
조정해야 합니다.

## RDK 의존성

```bash
source /opt/tros/humble/setup.bash
sudo apt update
sudo apt install -y python3-serial tros-humble-mono2d-body-detection
```

사람 탐지 예:

```bash
source /opt/tros/humble/setup.bash
cp -r /opt/tros/${TROS_DISTRO}/lib/mono2d_body_detection/config/ .
export CAM_TYPE=mipi
ros2 launch mono2d_body_detection mono2d_body_detection.launch.py
```

YDLIDAR 드라이버는 별도 터미널에서 먼저 실행합니다.

## 빌드

```bash
cd ~/rescue-beacon-robot/software/ros2
source /opt/tros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

## 실행

RDK에서 LiDAR 드라이버와 사람 탐지 노드를 먼저 실행한 다음:

```bash
ros2 launch rescue_beacon rescue_beacon.launch.py
```

Arduino 없이 ROS 로직만 실행할 때:

```bash
ros2 launch rescue_beacon rescue_beacon.launch.py enable_serial:=false
```

사람 탐지 없이 LiDAR/상태 머신만 실행할 때:

```bash
ros2 launch rescue_beacon rescue_beacon.launch.py \
  enable_person:=false enable_serial:=false
```

## 주요 토픽

| Topic | Type | Purpose |
|---|---|---|
| `/scan` | `sensor_msgs/msg/LaserScan` | LiDAR |
| `/hobot_mono2d_body_detection` | `ai_msgs/msg/PerceptionTargets` | 사람 탐지 |
| `/search_cmd_vel` | `geometry_msgs/msg/Twist` | 탐색 주행 후보 |
| `/person_cmd_vel` | `geometry_msgs/msg/Twist` | 사람 접근 후보 |
| `/person_detected` | `std_msgs/msg/Bool` | 사람 탐지 여부 |
| `/person_close` | `std_msgs/msg/Bool` | 근접 프록시 |
| `/mission_state` | `std_msgs/msg/String` | SEARCH/CONFIRM/APPROACH/ALERT |
| `/cmd_vel` | `geometry_msgs/msg/Twist` | 최종 안전 주행 명령 |
| `/beacon_trigger` | `std_msgs/msg/Bool` | 음향 안내 트리거 |

## 반드시 확인할 하드웨어 설정

`config/rescue_beacon.yaml`에서 Arduino 포트가 실제 장치와 맞는지 확인합니다.

```bash
ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null
```

Arduino 펌웨어의 모터 핀, 모터 방향 반전값, 최대 선속도/각속도는 실제 배선에
맞춰야 합니다.

> 이 코드는 대회용 MVP 통합본입니다. 실제 사람 주변 주행 전에는 바퀴를 띄운
> 상태에서 모터 방향과 비상 정지를 최소 1회 확인하십시오.
