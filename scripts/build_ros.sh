#!/usr/bin/env bash
set -eo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# RDK X5의 TROS 환경을 읽고 이 저장소의 ROS 패키지만 빌드한다.
source /opt/tros/humble/setup.bash
cd "$repo_root/software/ros2"
colcon build --symlink-install --packages-select rescue_beacon
