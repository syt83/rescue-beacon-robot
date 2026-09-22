# ROS2 패키지 (RDK X5)

RDK X5 상에서 실행되는 ROS2 패키지입니다.

## 구조 (예정)

```
software/ros2/
└── rescue_beacon/
    ├── package.xml
    ├── setup.py                       # (또는 CMakeLists.txt, C++ 패키지인 경우)
    ├── rescue_beacon/
    │   ├── serial_bridge_node.py      # Arduino와 시리얼 통신
    │   ├── lidar_nav_node.py          # YDLIDAR 기반 장애물 회피/주행
    │   ├── beacon_controller_node.py  # 탐지 결과에 따라 음성 안내 트리거
    │   └── position_publisher.py      # 요구조자 위치 퍼블리시
    └── launch/
        └── rescue_beacon.launch.py
```

## 주요 토픽 (예정)

| 토픽 | 타입 | 설명 |
|---|---|---|
| `/scan` | `sensor_msgs/LaserScan` | YDLIDAR X4 Pro 스캔 데이터 |
| `/detected_person` | (커스텀) | perception 파이프라인의 탐지 결과 |
| `/rescue_target_pose` | `geometry_msgs/PoseStamped` | 요구조자 추정 위치 |
| `/cmd_vel` | `geometry_msgs/Twist` | 주행 명령 (Arduino로 전달) |

## 빌드

```bash
cd software/ros2
colcon build
source install/setup.bash
ros2 launch rescue_beacon rescue_beacon.launch.py
```
