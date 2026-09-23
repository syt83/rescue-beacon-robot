#!/usr/bin/env bash
set -eo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runtime_dir="$HOME/rdk_model_zoo/samples/vision/ultralytics_yolo/runtime/python"
model_file="$HOME/best_bayese_640x640_nv12.bin"

if [[ ! -f "$runtime_dir/ros_yolo_live.py" ]]; then
    echo "Missing YOLO runtime: $runtime_dir/ros_yolo_live.py" >&2
    exit 1
fi
if [[ ! -f "$model_file" ]]; then
    echo "Missing YOLO model: $model_file" >&2
    exit 1
fi

source /opt/tros/humble/setup.bash
cd "$runtime_dir"
export PYTHONPATH="$PWD:${PYTHONPATH:-}"
exec python3 "$repo_root/software/perception/ros_yolo_bridge.py"
