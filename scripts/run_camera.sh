#!/usr/bin/env bash
set -eo pipefail

# 스테레오 카메라 드라이버를 실행한다. YOLO보다 먼저 시작한다.
source /opt/tros/humble/setup.bash
exec ros2 launch mipi_cam mipi_cam_dual_channel.launch.py
