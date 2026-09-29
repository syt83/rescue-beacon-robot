#!/usr/bin/env bash
set -euo pipefail

# The ROS LiDAR process must be stopped first because it owns the serial port.
port="${1:-/dev/ttyUSB0}"
build_dir="$(mktemp -d)"
trap 'rm -rf "$build_dir"' EXIT
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
g++ -std=c++14 -O2 "$script_dir/check_lidar_sdk.cpp" \
    -o "$build_dir/check_lidar_sdk" \
    $(pkg-config --cflags --libs YDLIDAR_SDK)
timeout --signal=INT --kill-after=3s 25s "$build_dir/check_lidar_sdk" "$port"
