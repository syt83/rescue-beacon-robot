# ROS 2 소프트웨어

`rescue_beacon/`은 RDK X5에서 실행하는 Python ROS 2 패키지입니다.
실제 구현 노드는 `lidar_nav_node`, `person_follow_node`,
`mission_controller_node`, `serial_bridge_node`입니다.

```bash
cd ~/rescue_ws/rescue-beacon-robot
bash scripts/build_ros.sh
bash scripts/run_mission.sh
```

기본 실행은 Arduino 시리얼과 모터 전달이 모두 꺼져 있습니다.
전체 실행 및 하드웨어 순서는
[대회 실행 안내](../../docs/competition-runbook.md),
노드와 토픽은 [패키지 README](rescue_beacon/README.md)를 보세요.
