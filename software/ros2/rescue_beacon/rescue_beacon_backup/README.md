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