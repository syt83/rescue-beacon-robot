#!/usr/bin/env python3
"""사용자가 바퀴를 띄우고 직접 확인한 뒤 Nano Every 모터를 짧게 시험한다."""

import argparse
import sys
import time

import serial

STOP_COMMAND = b'CMD,0.000,0.000\n'


def read_lines(board, counts):
    """이미 도착한 텔레메트리를 읽어 마지막 엔코더 값을 보관한다."""
    while board.in_waiting:
        line = board.readline().decode('utf-8', 'replace').strip()
        if line.startswith('ENC,'):
            try:
                _, left, right = line.split(',')
                counts[:] = [int(left), int(right)]
            except ValueError:
                print(f'Invalid encoder line: {line}', file=sys.stderr)
        elif line.startswith('ERR,'):
            print(f'Arduino error: {line}', file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', default='/dev/ttyACM0')
    parser.add_argument('--wheels-up', action='store_true', required=True,
                        help='두 바퀴가 지면에서 떨어지고 차체가 고정된 상태')
    parser.add_argument('--linear', type=float, default=0.04)
    parser.add_argument('--duration', type=float, default=0.5)
    parser.add_argument('--wheel', choices=('both', 'left', 'right'), default='both')
    args = parser.parse_args()
    if not 0.0 < args.linear <= 0.08:
        parser.error('--linear 범위는 0 초과 0.08 m/s 이하입니다')
    if not 0.0 < args.duration <= 1.0:
        parser.error('--duration 범위는 0 초과 1.0초 이하입니다')
    angular = 0.0
    if args.wheel == 'left':
        angular = -3.5 * args.linear
    elif args.wheel == 'right':
        angular = 3.5 * args.linear

    print(f'시험 예정: {args.wheel} 바퀴, {args.linear:.2f} m/s, {args.duration:.1f}초')
    print('두 바퀴가 공중에 고정되어 있는지, 메인 전원 스위치에 손이 닿는지 확인하세요.')
    print('중지: 이 터미널에서 Ctrl+C. 그래도 바퀴가 돌면 즉시 메인 전원을 끄세요.')
    try:
        if input('위 조건을 직접 확인했으면 RUN을 입력하세요: ').strip() != 'RUN':
            print('시험 취소: RUN 확인이 없습니다.')
            return 1
    except (EOFError, KeyboardInterrupt):
        print('\n시험 취소: 직접 확인을 입력하지 않았습니다.')
        return 1

    try:
        board = serial.Serial(
            args.port, 115200, timeout=0.1,
            write_timeout=0.5, exclusive=True,
        )
    except serial.SerialException as exc:
        print(f'Cannot open {args.port}: {exc}', file=sys.stderr)
        return 2

    counts = [None, None]
    ready = False
    moved = False
    try:
        # 호환 펌웨어가 READY,1을 보낸 뒤에만 모터 명령을 허용한다.
        deadline = time.monotonic() + 8.0
        last_hello = 0.0
        while time.monotonic() < deadline:
            now = time.monotonic()
            if now - last_hello >= 0.5:
                board.write(b'HELLO\n')
                last_hello = now
            line = board.readline().decode('utf-8', 'replace').strip()
            if line == 'READY,1':
                ready = True
                break
        if not ready:
            print('No READY,1; motor test cancelled.', file=sys.stderr)
            return 1

        board.write(STOP_COMMAND)
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline and None in counts:
            read_lines(board, counts)
            time.sleep(0.05)
        if None in counts:
            print('No encoder telemetry; motor test cancelled.', file=sys.stderr)
            return 1
        # 0 명령 중 엔코더가 움직이면 의도하지 않은 회전으로 보고 시험하지 않는다.
        stationary_counts = tuple(counts)
        deadline = time.monotonic() + 0.6
        while time.monotonic() < deadline:
            board.write(STOP_COMMAND)
            read_lines(board, counts)
            if tuple(counts) != stationary_counts:
                print('Encoder changed while speed was zero. Motor test cancelled.',
                      file=sys.stderr)
                return 1
            time.sleep(0.1)
        start_counts = tuple(counts)

        print(
            f'READY,1; wheel={args.wheel}, linear={args.linear:.2f}, '
            f'angular={angular:.2f}, duration={args.duration:.1f}s'
        )
        deadline = time.monotonic() + args.duration
        while time.monotonic() < deadline:
            board.write(f'CMD,{args.linear:.3f},{angular:.3f}\n'.encode('ascii'))
            moved = True
            read_lines(board, counts)
            time.sleep(0.1)
        board.write(STOP_COMMAND)
        time.sleep(0.3)
        read_lines(board, counts)

        delta = (counts[0] - start_counts[0], counts[1] - start_counts[1])
        print(f'Encoder delta: left={delta[0]}, right={delta[1]}')
        print('속도 0 전송 완료. 바퀴가 실제로 멈췄는지 눈으로 확인하세요.')
        print('계속 돌면 코드가 끝났더라도 즉시 메인 전원 스위치를 끄세요.')
        expected = (0, 1) if args.wheel == 'both' else ((0,) if args.wheel == 'left' else (1,))
        if any(delta[index] == 0 for index in expected):
            print('A commanded wheel encoder did not change.', file=sys.stderr)
            return 1
        return 0
    except serial.SerialException as exc:
        print(f'Serial error: {exc}', file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print('\nCtrl+C 감지: 속도 0 명령을 보냅니다.')
        return 130
    finally:
        # 접지 또는 PWM 배선 오류에서는 0 명령이 실제 모터를 멈추지 못할 수 있다.
        if ready:
            for _ in range(3):
                try:
                    board.write(STOP_COMMAND)
                    time.sleep(0.05)
                except serial.SerialException:
                    break
        board.close()
        if moved:
            print('바퀴가 계속 돌면 메인 전원을 끄세요. 배선은 전원을 끈 뒤 만지세요.')


if __name__ == '__main__':
    raise SystemExit(main())
