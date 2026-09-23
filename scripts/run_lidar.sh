#!/usr/bin/env bash
set -eo pipefail

lidar_ws="$HOME/ydlidar_ros2_ws"
params_file="$lidar_ws/src/ydlidar_ros2_driver/params/X4-Pro.yaml"
if [[ ! -f "$lidar_ws/install/setup.bash" || ! -f "$params_file" ]]; then
    echo "Missing YDLIDAR workspace or X4-Pro.yaml under $lidar_ws" >&2
    exit 1
fi

source /opt/tros/humble/setup.bash
source "$lidar_ws/install/setup.bash"
exec ros2 launch ydlidar_ros2_driver ydlidar_launch.py "params_file:=$params_file"
