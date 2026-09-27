# YOLO 탐지 결과 ROS2 연결

`ros_yolo_bridge.py`는 이 장비의 기존
`/home/sunrise/rdk_model_zoo/samples/vision/ultralytics_yolo/runtime/python/ros_yolo_live.py`
노드를 재사용합니다. 화면용 JPEG와 함께 `/rescue_yolo_detections`
(`ai_msgs/msg/PerceptionTargets`)에 탐지 상자를 발행합니다.
모델의 `fallen`, `sit`, `standing` 세 클래스를 모두 `person`으로 전달합니다.
탐지 결과가 없는 프레임도 빈 메시지로 발행합니다.

카메라를 먼저 실행한 뒤 YOLO 터미널에서 저장소 최상위 경로 기준:

```bash
cd ~/rescue_ws/rescue-beacon-robot
bash scripts/run_yolo.sh
```

기존 `python3 ros_yolo_live.py`는 종료하고 위 명령을 실행해야 합니다.
같은 카메라와 모델을 두 프로세스에서 중복 실행하지 않습니다.
이 스크립트는 `~/rdk_model_zoo`의 기존 런타임과
`~/best_bayese_640x640_nv12.bin` 모델을 사용합니다. 해당 파일은 이
저장소에 포함되지 않습니다.

## YOLO 화면 모니터

기존 YOLO 런타임은 탐지 상자를 그린 JPEG 영상을
`/yolo/image_annotated/compressed`에 발행합니다. 카메라와 YOLO가 실행 중일 때
RDK의 새 터미널에서 아래 명령을 실행하면 브라우저 화면으로 볼 수 있습니다.
이 모니터는 영상·미션 상태·Arduino 연결 상태를 **읽기만** 하며 주행 명령은
보내지 않습니다.

```bash
cd ~/rescue_ws/rescue-beacon-robot
bash scripts/run_yolo_monitor.sh --host 0.0.0.0
```

RDK에 연결된 모니터에서는 `http://127.0.0.1:8088`을 엽니다. Ubuntu 노트북
화면에서는 RDK에서 `hostname -I`로 확인한 LAN 주소를 사용해
`http://<RDK_IP>:8088`을 엽니다. 두 장치는 같은 네트워크에 있어야 합니다.
창에 `영상 대기 중`이 계속 표시되면 카메라와 `run_yolo.sh`가 먼저 실행됐는지
확인합니다. 최종 통합 시험에서는 이 창을 열어 둔 채 로봇을 관찰합니다.

현재 사람 접근 정지는 실제 거리 대신 바운딩박스 높이 비율을 사용합니다.
`software/ros2/rescue_beacon/config/rescue_beacon.yaml`의 영상 크기 1920×1080과
`stop_height_ratio`는 실물 카메라 영상으로 확인해야 합니다.
터미널별 전체 실행 순서는 [대회 실행 안내](../../docs/competition-runbook.md)에
있습니다.
