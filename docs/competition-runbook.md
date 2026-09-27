# 대회 실행 및 하드웨어 시험 순서

기준 장비는 `/home/sunrise/rescue_ws/rescue-beacon-robot`에 이 저장소가 있고,
ROS 2 Humble/TROS, `~/ydlidar_ros2_ws`,
`~/rdk_model_zoo/samples/vision/ultralytics_yolo/runtime/python/ros_yolo_live.py`,
`~/best_bayese_640x640_nv12.bin`이 설치된 RDK X5입니다.
다른 장비에서는 이 외부 파일과 모델을 따로 준비하세요. 모델은 GitHub
저장소에 포함되지 않습니다.

## 0. 빌드

```bash
cd ~/rescue_ws/rescue-beacon-robot
bash scripts/build_ros.sh
```

빌드가 끝난 뒤에도 각 실행 터미널은 별도로 켜 둡니다. 종료할 때는 각
터미널에서 `Ctrl+C`를 누릅니다.

## 1. 배선 전 ROS 시험

아래 네 터미널을 순서대로 실행합니다. 미션 실행 기본값은
`enable_serial:=false`이므로 Arduino로 명령을 보내지 않습니다.

| 터미널 | 명령 | 확인할 것 |
| --- | --- | --- |
| 1 카메라 | `cd ~/rescue_ws/rescue-beacon-robot && bash scripts/run_camera.sh` | `/image_left_raw` |
| 2 YOLO | `cd ~/rescue_ws/rescue-beacon-robot && bash scripts/run_yolo.sh` | `/rescue_yolo_detections` |
| 3 LiDAR | `cd ~/rescue_ws/rescue-beacon-robot && bash scripts/run_lidar.sh` | `/scan` |
| 4 미션 | `cd ~/rescue_ws/rescue-beacon-robot && bash scripts/run_mission.sh` | `/mission_state`, `/cmd_vel` |

터미널 5에서:

```bash
source /opt/tros/humble/setup.bash
source ~/rescue_ws/rescue-beacon-robot/software/ros2/install/setup.bash
ros2 topic hz /scan
ros2 topic hz /rescue_yolo_detections
ros2 topic echo /mission_state --once
ros2 topic echo /cmd_vel --once
```

사람이 카메라에 충분히 크게 잡히면
`SEARCH → CONFIRM → APPROACH → ALERT`를 확인합니다.
`ALERT`에서 `/cmd_vel`은 0이며, 사람 영상이 사라져도 ALERT를 유지합니다.
새 탐색은 **터미널 4를 Ctrl+C로 종료하고 다시 실행**해야 시작합니다.
`stop_height_ratio: 0.72`는 1080픽셀 영상에서 사람 상자 높이 약
778픽셀을 뜻하며 실제 미터 거리가 아닙니다.

## 2. Arduino 펌웨어 업로드

먼저 [펌웨어 README](../firmware/arduino/README.md)의 제안 핀 배치와 실제
배선을 맞춥니다. 모터 전원은 끈 상태에서 Arduino Nano Every용 스케치를
업로드합니다. 지금 장치에 보이는 `Nano Every Ready` 문구는 이 저장소
펌웨어의 출력이 아니므로 업로드가 필요합니다.

업로드 후, 다른 시리얼 프로그램이 모두 종료된 상태에서:

```bash
cd ~/rescue_ws/rescue-beacon-robot
python3 scripts/arduino_smoke_test.py --port /dev/ttyACM0
```

`READY,1`, `ENC,...`, `SOUND,...`가 나와야 합니다. 이 스크립트는
주행 명령으로 0만 보냅니다. 포트가 바뀌면
`ls -l /dev/serial/by-id/`로 Nano Every를 찾아 `--port`에 넣습니다.
`/dev/ttyUSB0`은 이 장비의 LiDAR이므로 Arduino 포트로 쓰지 않습니다.

## 3. 음향·센서 시험 (모터 주행 잠금)

DFPlayer Mini와 PAM8403을 연결하고 FAT32 microSD의 `/mp3/0001.mp3`을
준비합니다. 먼저 ROS 없이 재생 명령을 시험합니다.

```bash
cd ~/rescue_ws/rescue-beacon-robot
python3 scripts/arduino_smoke_test.py --port /dev/ttyACM0 --beep
```

`ACK,BEEP`는 Arduino가 명령을 보냈다는 뜻입니다. 실제 소리가 나는지
귀로 확인하세요. 무음이면 전원, SD 카드, DAC→앰프, 스피커를 확인합니다.

ROS 연결 시험은 별도 터미널에서:

```bash
cd ~/rescue_ws/rescue-beacon-robot
bash scripts/run_serial_bridge.sh
```

이 스크립트는 `enable_motion=false`로 시작합니다. 다른 터미널에서:

```bash
source /opt/tros/humble/setup.bash
ros2 topic echo /arduino_ready --once
ros2 topic echo /arduino_telemetry --once
ros2 topic echo /sound_detected --once
ros2 topic pub --once /beacon_trigger std_msgs/msg/Bool "{data: true}"
```

`/arduino_ready`가 `true`여야 합니다. `/arduino_telemetry`에
`ENC,...`와 재생 시 `ACK,BEEP`가 보입니다. LM393은
`/sound_detected`에 0/1로 나타납니다. LM393 한 개로는 소리 방향을
추정할 수 없어서 미션 주행에는 아직 쓰지 않습니다.
시험이 끝나면 시리얼 브리지 터미널에서 `Ctrl+C`를 누릅니다.

## 4. 모터·엔코더 시험 (바퀴를 띄운 상태)

모터 드라이버·엔코더 배선을 확인하고, 바퀴가 지면에 닿지 않도록
차체를 고정합니다. 모터 전원 차단 수단을 손이 닿는 곳에 둡니다.
카메라·LiDAR·미션 노드는 종료하고 `ros2 topic info /cmd_vel`에서
기존 퍼블리셔가 없는지 확인합니다.

터미널 A:

```bash
cd ~/rescue_ws/rescue-beacon-robot
bash scripts/run_serial_bridge.sh --enable-motion
```

`/arduino_ready: true`가 된 뒤 모터 전원을 켜고, 터미널 B에서 짧은
저속 명령을 보냅니다.

```bash
source /opt/tros/humble/setup.bash
timeout 3s ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.04}, angular: {z: 0.0}}"
```

명령이 끝난 뒤 0.5초 이내에 두 바퀴가 멈추는지, 같은 방향으로 도는지,
`/arduino_telemetry`의 `ENC` 값이 변하는지 확인합니다. 잘못된 방향이면
펌웨어의 `LEFT_MOTOR_INVERT`/`RIGHT_MOTOR_INVERT`와 실제 모터 극성을
조정하고 재업로드합니다. 장치가 멈추지 않으면 즉시 모터 전원을 끕니다.

## 5. 전체 통합

1. 터미널 1~3에서 카메라, YOLO, LiDAR를 실행합니다.
2. 터미널 4에서 먼저 `bash scripts/run_mission.sh enable_serial:=true`를
   실행합니다. 이때 **모터 전달은 여전히 꺼져 있습니다**.
3. `/arduino_ready: true`, 센서 토픽, `ALERT`에서 실제 음향 안내를
   확인합니다. 새 시험마다 터미널 4를 재시작합니다.
4. 바퀴를 띄운 상태에서
   `bash scripts/run_mission.sh enable_serial:=true enable_motion:=true`로
   재시작해 모터 방향과 정지를 확인합니다.
5. 마지막으로 넓고 사람이 없는 시험 공간에서 지상 주행을 검증합니다.
   사람이 있는 방향으로 접근할 때는 바운딩박스 기반 정지값
   `software/ros2/rescue_beacon/config/rescue_beacon.yaml`의
   `stop_height_ratio`를 실제 장착 높이와 시야에 맞게 조정합니다.

LiDAR 스캔이 끊기거나 전방 측정이 유효하지 않으면 ROS가 정지 명령을
보냅니다. ROS `/cmd_vel`이 끊기면 브리지가 0을 보내고, USB 통신이
끊기면 Arduino의 0.5초 감시 시간이 PWM을 0으로 만듭니다. 전원 차단
수단은 별도로 유지합니다.

## 코드 검증

하드웨어 없이 실행할 수 있는 ROS 안전 동작 테스트:

```bash
cd ~/rescue_ws/rescue-beacon-robot
source /opt/tros/humble/setup.bash
python3 -m unittest discover -s software/ros2/rescue_beacon/test -p "test_*.py" -v
```

Arduino Nano Every 대상 컴파일 명령은 [펌웨어 README](../firmware/arduino/README.md)에
있습니다. 실제 업로드와 모터·음향 시험 결과는 배선 후에만 확인할 수 있습니다.

## GitHub에 공유하기

모델 바이너리와 외부 YOLO 런타임은 저장소에 들어 있지 않습니다.
코드와 문서 변경을 확인한 뒤 직접 게시할 때:

```bash
cd ~/rescue_ws/rescue-beacon-robot
git status --short
git diff --check
git add README.md docs/competition-runbook.md firmware/arduino \
  scripts software/perception software/ros2/rescue_beacon software/ros2/README.md
git commit -m "Prepare rescue robot hardware bring-up and runbook"
git push origin main
```

게시할 때는 `git status --short`로 포함 파일을 확인하고,
모델 바이너리나 장치별 비밀 파일이 들어가지 않았는지 확인합니다.
