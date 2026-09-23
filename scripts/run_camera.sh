#!/usr/bin/env bash
set -eo pipefail

source /opt/tros/humble/setup.bash
exec ros2 launch mipi_cam mipi_cam_dual_channel.launch.py
