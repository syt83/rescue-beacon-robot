#!/usr/bin/env bash
set -eo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
install_setup="$repo_root/software/ros2/install/setup.bash"
if [[ ! -f "$install_setup" ]]; then
    echo "ROS package not built. Run: bash $repo_root/scripts/build_ros.sh" >&2
    exit 1
fi

source /opt/tros/humble/setup.bash
source "$install_setup"
exec ros2 launch rescue_beacon rescue_beacon.launch.py "$@"
