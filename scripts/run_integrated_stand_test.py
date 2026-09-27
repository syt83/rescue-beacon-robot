#!/usr/bin/env python3
"""Run the full ROS mission briefly while the robot wheels are off the floor.

This script does command motors. The operator must run it locally after securing
the robot on a stand, and keep a hand near the physical main power switch.
"""

import argparse
import os
from pathlib import Path
import signal
import subprocess
import threading
import time


ROOT = Path(__file__).resolve().parents[1]
MISSION = ROOT / 'scripts' / 'run_mission.sh'
READY_LOG = 'Arduino firmware protocol READY,1'


def check_no_other_motion_nodes():
    # 기존 미션/브리지가 남아 있으면 두 퍼블리셔가 모터를 동시에 제어할 수 있다.
    probe = subprocess.run(
        ['bash', '-lc', 'source /opt/tros/humble/setup.bash && ros2 node list'],
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    active = set(probe.stdout.splitlines())
    conflicts = active & {'/mission_controller_node', '/serial_bridge_node'}
    if conflicts:
        raise RuntimeError(f'기존 ROS 미션/브리지를 먼저 종료하세요: {sorted(conflicts)}')


def stop_group(process):
    # launch와 자식 ROS 노드가 같은 새 프로세스 그룹에 있으므로 함께 종료한다.
    for sig, pause in (
        (signal.SIGINT, 1.5),
        (signal.SIGTERM, 0.5),
        (signal.SIGKILL, 0.0),
    ):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            break
        if pause:
            time.sleep(pause)
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--seconds', type=float, default=2.0,
        help='Arduino READY 후 미션 구동 시간 (기본 2초, 최대 3초)',
    )
    args = parser.parse_args()
    if not 0 < args.seconds <= 3:
        parser.error('--seconds는 0초 초과 3초 이하여야 합니다')

    check_no_other_motion_nodes()
    print('바퀴가 공중에 뜬 받침대에 차체를 고정하고, 손은 바퀴에서 떼세요.', flush=True)
    print('바퀴가 멈추지 않으면 즉시 메인 전원 스위치를 끄세요.', flush=True)
    if input('준비됐으면 RUN 입력: ').strip() != 'RUN':
        print('시험 취소')
        return

    ready = threading.Event()
    process = subprocess.Popen(
        ['bash', str(MISSION), 'enable_serial:=true', 'enable_motion:=true'],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        start_new_session=True,
    )

    def show_logs():
        for line in process.stdout:
            print(line, end='', flush=True)
            if READY_LOG in line:
                ready.set()

    reader = threading.Thread(target=show_logs, daemon=True)
    reader.start()
    try:
        deadline = time.monotonic() + 15
        while not ready.is_set() and process.poll() is None:
            if time.monotonic() >= deadline:
                raise RuntimeError('Arduino READY가 15초 안에 오지 않아 중단합니다')
            time.sleep(0.05)
        if process.poll() is not None:
            raise RuntimeError('Arduino READY 전에 ROS 미션이 종료됐습니다')
        print(f'Arduino READY. {args.seconds:g}초 후 자동 종료합니다.', flush=True)
        deadline = time.monotonic() + args.seconds
        while time.monotonic() < deadline and process.poll() is None:
            time.sleep(0.05)
    finally:
        stop_group(process)
        reader.join(timeout=1)
        print('ROS 미션 종료. 두 바퀴가 실제로 멈췄는지 눈으로 확인하세요.', flush=True)


if __name__ == '__main__':
    main()
