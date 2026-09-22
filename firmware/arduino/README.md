# Arduino Nano Every 펌웨어

Arduino Nano Every에서 실행되는 저수준 제어 코드입니다.

## 역할

- Cytron MDD10A를 통한 구동 모터 PWM/방향 제어
- RB-35GM 엔코더 카운트 읽기
- LM393 소리 감지 모듈 인터럽트 처리
- RDK X5와 UART 시리얼로 명령/센서 데이터 송수신

## 구조 (예정)

```
firmware/arduino/
└── rescue_beacon_firmware/
    ├── rescue_beacon_firmware.ino   # 메인 스케치
    ├── motor_control.h / .cpp       # 모터 드라이버 제어
    ├── encoder.h / .cpp             # 엔코더 카운트
    └── sound_sensor.h / .cpp        # LM393 소리 감지
```

Arduino IDE 규칙상 `.ino` 파일명은 폴더명과 동일해야 합니다.

## 빌드/업로드

```bash
arduino-cli compile --upload -p <PORT> --fqbn arduino:megaavr:nona4809 rescue_beacon_firmware
```
