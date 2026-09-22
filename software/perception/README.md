# Perception (YOLO 기반 사람 탐지)

스테레오 카메라 입력을 받아 요구조자(사람)를 탐지하고 대략적인 거리를 추정하는 파이프라인입니다.

## 구조 (예정)

```
software/perception/
├── detect_person.py     # 스테레오 카메라 입력 → YOLO 추론 → 바운딩박스/신뢰도
├── stereo_depth.py       # 좌/우 카메라 시차 기반 거리 계산
├── models/                # 학습된 YOLO 가중치(.pt) — 용량 크면 Git LFS 또는 릴리스 첨부 권장
└── requirements.txt       # ultralytics, opencv-python 등
```

## 비고

- ROS2 노드([../ros2](../ros2))에서 이 파이프라인을 호출하거나, 별도 프로세스로 실행 후 토픽으로 결과를 퍼블리시하는 방식 중 선택
- `models/`에 원본 가중치 파일을 커밋할 경우 [.gitignore](../../.gitignore)에서 `*.pt` 예외 처리 필요
