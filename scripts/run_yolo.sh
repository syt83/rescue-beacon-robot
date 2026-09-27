#!/usr/bin/env bash
set -eo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# 기존 YOLO 런타임과 모델은 저장소 밖에 있으므로 경로를 먼저 확인한다.
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
# ros_yolo_bridge.py가 원본 ros_yolo_live.py를 import할 수 있게 한다.
export PYTHONPATH="$PWD:${PYTHONPATH:-}"
exec python3 "$repo_root/software/perception/ros_yolo_bridge.py"
