#!/usr/bin/env bash
set -eo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
install_setup="$repo_root/software/ros2/install/setup.bash"
motion=false
# --enable-motion을 명시하기 전에는 Arduino에 0 속도만 전달한다.
if [[ "${1:-}" == "--enable-motion" ]]; then
    motion=true
    shift
fi
if [[ ! -f "$install_setup" ]]; then
    echo "ROS package not built. Run: bash $repo_root/scripts/build_ros.sh" >&2
    exit 1
fi

source /opt/tros/humble/setup.bash
source "$install_setup"
exec ros2 run rescue_beacon serial_bridge_node --ros-args \
    --params-file "$repo_root/software/ros2/rescue_beacon/config/rescue_beacon.yaml" \
    -p "enable_motion:=$motion" "$@"
