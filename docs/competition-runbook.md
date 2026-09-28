# 대회 실행 및 하드웨어 시험 순서

기준 장비는 `/home/sunrise/rescue_ws/rescue-beacon-robot`에 이 저장소가 있고,
ROS 2 Humble/TROS, `~/ydlidar_ros2_ws`,
`~/rdk_model_zoo/samples/vision/ultralytics_yolo/runtime/python/ros_yolo_live.py`,
`~/best_bayese_640x640_nv12.bin`이 설치된 RDK X5입니다.
다른 장비에서는 이 외부 파일과 모델을 따로 준비하세요. 모델은 GitHub
저장소에 포함되지 않습니다.

이전 시험에서 속도 0 명령에도 바퀴가 돌아 메인 스위치로 정지한 적이
있습니다. 이후 사용자가 배선을 다시 연결해 양쪽 바퀴의 직선·곡선·회전
주행과 엔코더 동작을 확인했습니다. 받침대 위에서 ROS 브리지의 1회
전진 명령으로 양쪽 바퀴가 잠깐 돌고 멈춘 것도 확인했습니다.
ROS 회전 명령에서는 두 바퀴가 서로 반대 방향으로 잠깐 돌고 멈췄습니다.
**자율 주행은 아직 확인되지 않았습니다.** 추가 구동 시험은
차체를 받침대에 고정해 바퀴를 띄운 뒤 진행합니다. 전원을 켰을 때 명령 없이
바퀴가 돌면 즉시 메인 스위치를 끄고 시험을 중단합니다.

## 0. 빌드

```bash
cd ~/rescue_ws/rescue-beacon-robot
bash scripts/build_ros.sh
```

빌드가 끝난 뒤에도 각 실행 터미널은 별도로 켜 둡니다. 종료할 때는 각
터미널에서 `Ctrl+C`를 누릅니다.

## 0-1. 메인 전원을 끈 채 엔코더만 확인

엔코더를 다시 독립적으로 확인할 때는 노트북 USB로 Nano를 켜고
[센서 전용 Arduino 스케치](../firmware/arduino/README.md#모터-전원-없이-엔코더-확인)를
사용합니다. 왼쪽·오른쪽 바퀴를 손으로 각각 돌려 엔코더 카운트가 변하는지
확인합니다. 이 스케치에는 모터 구동 명령이 없습니다. RDK와 모터는 같은
메인 스위치에 연결되어 있으므로, Nano만 켤 때는 메인 스위치를 끕니다.

## 1. 모터 전달을 끈 ROS 시험

아래 네 터미널을 순서대로 실행합니다. 미션 실행 기본값은
`enable_serial:=false`이므로 Arduino로 명령을 보내지 않습니다.

| 터미널 | 명령 | 확인할 것 |
| --- | --- | --- |
| 1 카메라 | `cd ~/rescue_ws/rescue-beacon-robot && bash scripts/run_camera.sh` | `/image_left_raw` |
| 2 YOLO | `cd ~/rescue_ws/rescue-beacon-robot && bash scripts/run_yolo.sh` | `/rescue_yolo_detections` |
| 3 LiDAR | `cd ~/rescue_ws/rescue-beacon-robot && bash scripts/run_lidar.sh` | `/scan` |
| 4 미션 | `cd ~/rescue_ws/rescue-beacon-robot && bash scripts/run_mission.sh` | `/mission_state`, `/cmd_vel` |
| 5 YOLO 화면 | `cd ~/rescue_ws/rescue-beacon-robot && bash scripts/run_yolo_monitor.sh --host 0.0.0.0` | 브라우저의 탐지 상자 영상 |

RDK 모니터의 브라우저에서 `http://127.0.0.1:8088`을 열거나, 노트북에서는
RDK의 `hostname -I`로 확인한 주소로 `http://<RDK_IP>:8088`을 엽니다.
모니터는 `/yolo/image_annotated/compressed`를 읽기만 하고 모터 명령을
보내지 않습니다. 카메라·YOLO 실행 뒤에 열어 둡니다.

터미널 6에서:

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

2026-09-27 실물 ROS 시험에서 `/scan` 약 11.1 Hz,
`SEARCH → CONFIRM → APPROACH → ALERT`를 확인했습니다. `ALERT`에서
`/beacon_trigger: true`, `/cmd_vel`의 `linear.x: 0.0`과
`angular.z: 0.0`도 확인했습니다. `person_close`는 실시간 탐지값이어서
ALERT 이후 사람이 화면에서 멀어지면 `false`가 될 수 있지만,
미션 상태는 ALERT로 유지됩니다. 미션을 다시 시작하면 상태는 SEARCH부터
시작하므로, `/cmd_vel` 회전값은 **같은 실행에서 ALERT를 확인한 뒤에만**
ALERT 정지 시험의 결과로 해석합니다.

## 2. Arduino 펌웨어 업로드

먼저 [펌웨어 README](../firmware/arduino/README.md)의 회로도 핀 배치와 실제
배선을 맞춥니다. 주행 노드를 종료하고 차체를 고정한 상태에서 Arduino Nano
Every용 스케치를 업로드합니다. 이 장비는 RDK와 모터가 메인 스위치를 공유하므로
모터 전원만 따로 끌 수 없습니다. `Nano Every Ready` 문구가 보이면 이전 스케치가 실행 중인
것이므로 [펌웨어 README](../firmware/arduino/README.md)의 업로드 절차를
진행하세요. 2026-09-27에 이 장비에는 저장소 펌웨어를 업로드하고
`READY,1` 통신을 확인했습니다.

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

DFPlayer Pro DFR0768과 PAM8403을 연결하고 USB-C로 내장 저장공간에
`/bbibip.mp3`을 복사합니다. 저장소의 [테스트 음원과 복사 순서](../audio/README.md)를
사용할 수 있습니다. 먼저 ROS 없이 재생 명령을 시험합니다.

```bash
cd ~/rescue_ws/rescue-beacon-robot
python3 scripts/arduino_smoke_test.py --port /dev/ttyACM0 --beep
```

`ACK,BEEP`는 Arduino가 명령을 보냈다는 뜻입니다. 실제 소리가 나는지
귀로 확인하세요. 무음이면 Pro용 펌웨어 업로드, 파일 경로, 전원,
DAC→앰프, 스피커를 확인합니다.

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

**이전 문제와 현재 상태:** 2026-09-27 왼쪽 MD20A의 GND 선을 다시 꽂은 뒤
바퀴가 계속 돌았습니다. 당시 어느 쪽 바퀴가 돌았는지는 왼쪽 회전만으로
확정할 수 없습니다. 주행 프로세스가 없었고 속도 0 명령을 두 번 보내도
멈추지 않아 메인 스위치로 정지했습니다. 이후 사용자가 배선을 다시 하고
양쪽 모터의 직선·곡선·회전 주행과 엔코더 동작을 확인했습니다. 이 결과는
사용자 보고입니다. 이후 ROS 브리지로 1회 전진 명령을 보내 양쪽 바퀴가
잠깐 돌고 멈춘 것을 확인했습니다. ROS 회전에서도 두 바퀴가 반대 방향으로
잠깐 돌고 멈췄습니다. 자율 주행은 남아 있습니다.

다음 시험부터 실행 명령을 사용자에게 먼저 보여주고, 사용자가 자신의
터미널에서 직접 실행합니다. 스크립트는 시험 조건을 보여준 뒤 `RUN` 입력을
받아야 구동하고 기본 실행 시간은 0.5초입니다. 해당 터미널의 `Ctrl+C`로
스크립트를 중단할 수 있습니다. `Ctrl+C`나 속도 0 명령으로도 바퀴가 멈추지 않으면 즉시 메인
스위치를 끕니다. 이 장비는 RDK와 모터가 같은 스위치를 사용하므로 원격
연결도 끊깁니다.

모터 드라이버·엔코더 배선을 확인하고, 바퀴가 지면에 닿지 않도록
차체를 고정합니다. 메인 전원 스위치에 손이 닿도록 합니다.
먼저 ROS 없이 Arduino만 시험합니다. 배선이 확인된 뒤 아래 명령을 사용자
터미널에서 실행하면 호환 펌웨어와 정지 상태를 확인하고 0.5초간 0.04 m/s
전진 명령을 보낸 뒤 속도 0 명령을 보냅니다. 실제 정지는 눈으로 확인합니다.

```bash
cd ~/rescue_ws/rescue-beacon-robot
python3 scripts/arduino_motor_test.py --port /dev/ttyACM0 --wheels-up
```

두 바퀴가 전진 방향으로 돌고 멈추는지, `Encoder delta`의 좌우 값이 모두
변하는지 확인하세요. 모터가 멈추지 않으면 즉시 메인 전원을 끕니다.
배선을 만질 때도 메인 전원을 끕니다.

2026-09-27 시험에서는 오른쪽 바퀴만 돌았고 좌우 엔코더 값은 모두 0이었습니다.
왼쪽만 명령한 두 번의 시험에서는 어느 바퀴도 돌지 않았습니다. 이후
MD20A 자체 테스트 버튼으로 양쪽 바퀴가 각각 도는 것을 확인했습니다.
자체 테스트 버튼은 누르는 동안 모터를 최고 속도로 돌리므로 차체를
안정적으로 고정하고 아주 짧게 누릅니다. 모터와 드라이버의 전원·출력
경로는 동작합니다. 왼쪽만 0.5초 명령을 보낸 추가 시험에서도 왼쪽 바퀴와
MD20A 출력 LED가 모두 반응하지 않았습니다. 이후 배선을 다시 한 뒤
양쪽 구동을 확인했습니다.
배선을 바꾸기 전에는 메인 전원을 끕니다.
초기 시험에서 좌우 엔코더 값은 모두 0이었지만, GND 재연결 후 정지 명령
시험에서는 `ENC,-29,-9`, `ENC,-32,-17`이 읽혔습니다. 이후 사용자가 배선을
다시 하고 엔코더 동작을 확인했습니다. 당시 초기 카운트만으로는 좌우
엔코더와 실제 바퀴의 대응 관계를 판단하지 않았습니다.
MD20A의 자체 테스트 버튼과 출력 LED는
[제조사 데이터시트](https://cdn.robotshop.com/media/c/cyt/rb-cyt-254/pdf/md20a_datasheet.pdf)에 나옵니다.

카메라·LiDAR·미션 노드는 종료하고 `ros2 topic info /cmd_vel`에서
기존 퍼블리셔가 없는지 확인합니다.

터미널 A:

```bash
cd ~/rescue_ws/rescue-beacon-robot
bash scripts/run_serial_bridge.sh --enable-motion
```

모터·엔코더가 모두 정상 확인되고 `/arduino_ready: true`가 된 뒤 터미널 B에서 짧은
저속 명령을 보냅니다.

```bash
source /opt/tros/humble/setup.bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 0.10}, angular: {z: 0.0}}'
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 0.0}, angular: {z: 0.0}}'
```

명령이 끝난 뒤 0.5초 이내에 두 바퀴가 멈추는지, 같은 방향으로 도는지,
`/arduino_telemetry`의 `ENC` 값이 변하는지 확인합니다. 잘못된 방향이면
펌웨어의 `LEFT_MOTOR_INVERT`/`RIGHT_MOTOR_INVERT`와 실제 모터 극성을
조정하고 재업로드합니다. 장치가 멈추지 않으면 즉시 메인 전원을 끕니다.

## 5. 전체 통합

1. 터미널 1~3에서 카메라, YOLO, LiDAR를 실행하고 터미널 5의 YOLO
   화면을 브라우저에 띄워 탐지 상자를 보면서 진행합니다.
2. 터미널 4에서 먼저 `bash scripts/run_mission.sh enable_serial:=true`를
   실행합니다. 이때 **모터 전달은 여전히 꺼져 있습니다**.
3. `/arduino_ready: true`, 센서 토픽, `ALERT`에서 실제 음향 안내를
   확인합니다. 새 시험마다 터미널 4를 재시작합니다.
4. 바퀴를 띄운 상태에서
   아래의 시간 제한 시험을 사용해 모터 방향과 정지를 확인합니다. 기존
   미션과 브리지를 먼저 종료해야 합니다. Arduino가 `READY,1`을 알린 후
   기본 2초 동안만 모터 전달을 켭니다. 터미널에서 `RUN`을 입력해야 시작하며,
   바퀴가 멈추지 않으면 즉시 메인 전원 스위치를 끕니다.

   ```bash
   cd ~/rescue_ws/rescue-beacon-robot
   python3 scripts/run_integrated_stand_test.py
   ```
5. 마지막으로 넓고 사람이 없는 시험 공간에서 바닥의 짧은 직진을 먼저
   검증합니다. 받침대 시험처럼 `RUN`을 입력해야 시작하고 Arduino READY 후
   기본 2초 안에 자동 종료합니다. 전방 1m를 비우고 메인 스위치를 바로
   끌 수 있는 위치에서 실행합니다.

   ```bash
   cd ~/rescue_ws/rescue-beacon-robot
   python3 scripts/run_integrated_floor_test.py
   ```

   두 바퀴가 실제로 멈춘 뒤 사람 탐색·접근 주행을 별도 시험합니다.
   사람이 있는 방향으로 접근할 때는 바운딩박스 기반 정지값
   `software/ros2/rescue_beacon/config/rescue_beacon.yaml`의
   `stop_height_ratio`를 실제 장착 높이와 시야에 맞게 조정합니다.
   목표 사람은 로봇 전방 1~2m에 서고, 다른 사람은 전원 스위치 옆에서
   노트북 YOLO 화면을 관찰합니다. 아래 명령은 Arduino READY 후 최대 8초,
   `ALERT`가 나오면 정지 상태를 1초 관찰한 뒤 ROS를 종료합니다.

   ```bash
   cd ~/rescue_ws/rescue-beacon-robot
   python3 scripts/run_person_mission_trial.py
   ```

LiDAR 스캔이 끊기거나 전방 측정이 유효하지 않으면 ROS가 정지 명령을
보냅니다. ROS `/cmd_vel`이 끊기면 브리지가 0을 보내고, USB 통신이
끊기면 Arduino의 0.5초 감시 시간이 PWM을 0으로 만듭니다. 전원 차단
수단은 별도로 유지합니다.
전방 0.50m 이내에 유효한 장애물 측정값이 있으면 직선·회전 속도를 모두
0으로 만듭니다.
이 로봇은 LiDAR의 원시 스캔 약 180°가 차체 정면입니다. 실제 정면에 세운
상자는 원시 스캔 173° 부근에서 0.43m로 측정됐습니다. 따라서
`rescue_beacon.yaml`의 두 `scan_yaw_offset_deg`를 180.0으로 설정했습니다.
LiDAR를 다시 장착하면 정면 물체의 원시 각도를 확인하고 두 값을 함께
고쳐야 합니다. 스캔 높이에 닿지 않는 낮은 물체는 감지되지 않습니다.
2026-09-27 모터 전달을 끈 통합 시험에서 정면 상자 0.43m일 때
`SEARCH` 상태의 `/cmd_vel`은 직선·회전 모두 0이었고, 상자를 치우자
전진 0.14m/s로 돌아왔습니다.

## 코드 검증

하드웨어 없이 실행할 수 있는 ROS 안전 동작 테스트:

```bash
cd ~/rescue_ws/rescue-beacon-robot
source /opt/tros/humble/setup.bash
python3 -m unittest discover -s software/ros2/rescue_beacon/test -p "test_*.py" -v
```

Arduino Nano Every 대상 컴파일 명령과 업로드 결과는
[펌웨어 README](../firmware/arduino/README.md)에 있습니다. 모터·음향의
자율 주행과 음향 출력은 아직 확인되지 않았습니다.

## GitHub에 공유하기

모델 바이너리와 외부 YOLO 런타임은 저장소에 들어 있지 않습니다.
기존 코드 전체가 들어 있는 `fix/md20a-safe-bringup` 브랜치에 변경을 게시하고
Pull Request로 검토합니다. `main`에 직접 푸시하지 않습니다.
기여자 목록과 프로필의 커밋 기여는 GitHub 계정에 연결된 이메일로 작성한
커밋이 기본 브랜치에 병합되어야 반영됩니다. 자세한 조건은
[GitHub 기여자 안내](https://docs.github.com/en/repositories/viewing-activity-and-data-for-your-repository/viewing-a-projects-contributors)에 있습니다.
로컬에서 게시할 때:

```bash
cd ~/rescue_ws/rescue-beacon-robot
git status --short
git diff --check
git switch fix/md20a-safe-bringup
git add README.md docs firmware hardware/bom/README.md scripts
git commit -m "Align MD20A wiring and make motor bring-up safer"
git push -u origin fix/md20a-safe-bringup
```

게시할 때는 `git status --short`로 포함 파일을 확인하고,
모델 바이너리나 장치별 비밀 파일이 들어가지 않았는지 확인합니다.
