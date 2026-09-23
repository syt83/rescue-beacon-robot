#!/usr/bin/env bash
set -eo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source /opt/tros/humble/setup.bash
cd "$repo_root/software/ros2"
colcon build --symlink-install --packages-select rescue_beacon
