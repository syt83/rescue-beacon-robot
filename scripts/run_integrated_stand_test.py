#!/usr/bin/env python3
"""Run the full ROS mission briefly on a stand or in a clear floor area.

This script does command motors. The operator must run it locally and keep a
hand near the physical main power switch.
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
ALERT_LOG = 'STATE APPROACH -> ALERT'
SLOW_LINEAR_SPEED = 0.05
SLOW_ANGULAR_SPEED = 0.20


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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--floor', action='store_true',
        help='바닥에서 짧게 실행 (최대 2초)',
    )
    parser.add_argument(
        '--until-alert', action='store_true',
        help='사람 목표를 향해 주행하고 ALERT 후 1초 관찰 (바닥 전용)',
    )
    parser.add_argument(
        '--seconds', type=float, default=2.0,
        help='Arduino READY 후 미션 구동 시간 (기본 2초)',
    )
    parser.add_argument(
        '--slow', action='store_true',
        help='Arduino에 보낼 속도를 전진 0.05 m/s, 회전 0.20 rad/s 이하로 제한',
    )
    parser.add_argument(
        '--no-audio', action='store_true',
        help='ALERT에서 Arduino에 BEEP 명령을 보내지 않음',
    )
    parser.add_argument(
        '--search-only', action='store_true',
        help='사람 추적을 끄고 LiDAR 탐색 주행만 확인',
    )
    parser.add_argument(
        '--camera-only', action='store_true',
        help='LiDAR 없이 YOLO 사람 접근만 2초 이내 감독하 시험',
    )
    args = parser.parse_args(argv)
    if args.until_alert and not args.floor:
        parser.error('--until-alert는 바닥 시험에서만 사용할 수 있습니다')
    if args.until_alert and args.search_only:
        parser.error('--until-alert와 --search-only는 함께 사용할 수 없습니다')
    if args.camera_only and (not args.floor or args.until_alert or args.search_only):
        parser.error('--camera-only는 --floor와 함께 단독으로만 사용합니다')
    if args.camera_only and (not args.slow or not args.no_audio):
        parser.error('--camera-only에는 --slow --no-audio가 필요합니다')
    max_seconds = 2 if args.camera_only else (8 if args.until_alert else (2 if args.floor else 3))
    if not 0 < args.seconds <= max_seconds:
        parser.error(f'--seconds는 0초 초과 {max_seconds}초 이하여야 합니다')

    check_no_other_motion_nodes()
    if args.floor:
        if args.camera_only:
            print('누운 사람 한 명만 카메라에 보이게 하고, 보조자는 화면 밖에서 전원 스위치를 잡으세요.', flush=True)
            print('LiDAR 장애물 감지가 없으므로 주행 경로와 사람 앞을 비우세요.', flush=True)
            print('배터리 온도가 정상일 때만 실행하세요.', flush=True)
        elif args.until_alert:
            print('목표 사람은 로봇 앞 1~2m에 서고, 다른 사람은 전원 스위치 옆에서 화면을 보세요.', flush=True)
        else:
            print('평평한 바닥에 놓고 전방 1m를 비우세요. 사람은 카메라 화면 밖에 있어야 합니다.', flush=True)
    else:
        print('바퀴가 공중에 뜬 받침대에 차체를 고정하고, 손은 바퀴에서 떼세요.', flush=True)
    if args.slow:
        print(
            f'저속 제한: 전진 {SLOW_LINEAR_SPEED:.2f} m/s, '
            f'회전 {SLOW_ANGULAR_SPEED:.2f} rad/s 이하.', flush=True
        )
    if args.no_audio:
        print('음향 명령은 보내지 않습니다.', flush=True)
    if args.search_only:
        print('사람 추적을 끄고 LiDAR 탐색 주행만 확인합니다.', flush=True)
    if args.camera_only:
        print('탐색 회전은 끄고, 사람 탐지 전에는 움직이지 않습니다.', flush=True)
    print('바퀴가 멈추지 않으면 즉시 메인 전원 스위치를 끄세요.', flush=True)
    if input('준비됐으면 RUN 입력: ').strip() != 'RUN':
        print('시험 취소')
        return

    ready = threading.Event()
    alert = threading.Event()
    launch_command = [
        'bash', str(MISSION), 'enable_serial:=true', 'enable_motion:=true',
        'log_motor_commands:=true',
    ]
    if args.search_only:
        launch_command.append('enable_person:=false')
    if args.camera_only:
        launch_command.append('camera_only:=true')
    if args.slow:
        launch_command.extend([
            f'max_linear_speed:={SLOW_LINEAR_SPEED}',
            f'max_angular_speed:={SLOW_ANGULAR_SPEED}',
        ])
    if args.no_audio:
        launch_command.append('enable_audio:=false')
    process = subprocess.Popen(
        launch_command,
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
            if ALERT_LOG in line:
                alert.set()

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
        if args.until_alert:
            print(f'Arduino READY. ALERT가 나오거나 {args.seconds:g}초가 지나면 종료합니다.', flush=True)
        else:
            print(f'Arduino READY. {args.seconds:g}초 후 자동 종료합니다.', flush=True)
        deadline = time.monotonic() + args.seconds
        while time.monotonic() < deadline and process.poll() is None:
            if args.until_alert and alert.is_set():
                print('ALERT 확인. 정지 상태를 1초 관찰합니다.', flush=True)
                time.sleep(1)
                break
            time.sleep(0.05)
        if args.until_alert and not alert.is_set():
            print('시간 제한 안에 ALERT에 도달하지 못했습니다.', flush=True)
    finally:
        if args.camera_only and process.poll() is None:
            # 정지 요청을 래치하고 감속할 시간을 준 뒤 ROS를 종료한다.
            try:
                stop_request = subprocess.run(
                    [
                        'bash', '-lc',
                        'source /opt/tros/humble/setup.bash && '
                        'ros2 topic pub --once /trial_stop '
                        'std_msgs/msg/Bool "{data: true}"',
                    ],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    start_new_session=True,
                )
                if stop_request.returncode == 0:
                    time.sleep(0.8)
                else:
                    print('감속 요청 실패; 즉시 정지 명령으로 종료합니다.', flush=True)
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                print('감속 요청 중단; 즉시 정지 명령으로 종료합니다.', flush=True)
        stop_group(process)
        reader.join(timeout=1)
        print('ROS 미션 종료. 두 바퀴가 실제로 멈췄는지 눈으로 확인하세요.', flush=True)


if __name__ == '__main__':
    main()
