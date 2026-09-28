#!/usr/bin/env bash
set -eo pipefail

# YOLO가 이미 발행하는 상자 표시 영상을 브라우저로 보여준다.
# 기본값은 RDK의 로컬 브라우저만 접속 가능하다. 노트북에서는 --host 0.0.0.0.
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source /opt/tros/humble/setup.bash
exec python3 "$repo_root/scripts/yolo_monitor.py" "$@"
