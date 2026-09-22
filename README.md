# rescue-beacon-robot

재난·재해 현장에서 자율적으로 이동하며 요구조자(구조 대상자)를 탐지하고, 발견 시 음향 신호로 구조대에게 위치를 알려주는 탐색 로봇 프로젝트입니다.

## 개요

붕괴 현장이나 접근이 어려운 재난 지역에서는 사람이 직접 들어가 수색하기 위험한 경우가 많습니다. 이 로봇은 소리 감지 센서와 스테레오 카메라 기반 사람 탐지, LiDAR 기반 장애물 회피를 결합해 좁고 불안정한 공간을 자율 주행하며 요구조자를 탐색하고, 발견 시 즉시 음성 안내를 재생해 구조대가 정확한 위치를 파악할 수 있도록 돕습니다.

## 하드웨어 구성

| 구분 | 부품 | 사양 |
|---|---|---|
| 메인 컴퓨터 | RDK X5 | 온보드 AI 추론, ROS2 실행 |
| 마이크로컨트롤러 | Arduino Nano Every | 모터 제어, 센서 인터페이스 |
| 모터 드라이버 | Cytron MDD10A | 듀얼 채널 DC 모터 드라이버 |
| 구동 모터 | RB-35GM+Encoder 21TYPE ×2 | 12V, 감속비 1:75, 엔코더 내장 |
| LiDAR | YDLIDAR X4 Pro | 2D 라이다, 장애물 회피/SLAM |
| 카메라 | RDK Stereo Camera Module | 스테레오 비전, 사람 탐지 |
| IMU | BNO085 | 자세 추정, 지자기 보정 |
| 음향 출력 | DFPlayer Mini + PAM8403 + 스피커 | 음성 안내 재생 |
| 소리 감지 | LM393 모듈 | 요구조자 반응(소리) 트리거 |
| 배터리 | 리튬이온 11.1V (3S) | 전원 공급 |

## 시스템 동작 흐름

1. **트리거**: LM393 소리 감지 모듈이 주변 소음/음성 반응을 감지하면 탐색 우선순위를 해당 방향으로 조정합니다.
2. **탐지**: 스테레오 카메라 영상을 YOLO 기반 사람 탐지 파이프라인에 입력해 요구조자 존재 여부와 대략적 거리를 추정합니다.
3. **주행**: YDLIDAR X4 Pro로 획득한 스캔 데이터를 기반으로 장애물을 회피하며 경로를 탐색합니다(SLAM/로컬 플래닝).
4. **안내**: 요구조자가 확인되면 DFPlayer Mini + PAM8403 앰프를 통해 사전 녹음된 음성(예: "구조 신호 확인, 구조대가 오고 있습니다")을 재생합니다.
5. **보고**: 탐지된 요구조자의 위치(로봇 기준 상대 좌표 또는 맵 좌표)를 ROS2 토픽으로 퍼블리시해 상위 모니터링 시스템/구조대 콘솔에서 확인할 수 있도록 합니다.

## 저장소 구조

```
rescue-beacon-robot/
├── hardware/
│   ├── kicad/          # KiCad 회로도, PCB, 심볼 라이브러리
│   └── bom/            # 부품 목록(BOM)
├── firmware/
│   └── arduino/        # Arduino Nano Every 펌웨어 (모터/센서 제어)
├── software/
│   ├── ros2/           # RDK X5용 ROS2 패키지 (주행, 통신, 상태 관리)
│   └── perception/     # YOLO 기반 사람 탐지 파이프라인
└── docs/
    └── images/         # 시스템 다이어그램, 사진
```

## 개발 환경

- **RDK X5**: Ubuntu + ROS2, Python 기반 인식/주행 노드
- **Arduino Nano Every**: Arduino IDE 또는 arduino-cli, C++
- **KiCad**: 회로도 및 PCB 설계 (버전 7 이상 권장)

## 시작하기

```bash
# ROS2 패키지 빌드 (RDK X5 상에서)
cd software/ros2
colcon build

# Arduino 펌웨어 업로드
cd firmware/arduino
arduino-cli compile --upload -p <PORT> --fqbn arduino:megaavr:nona4809
```

## 라이선스

MIT
