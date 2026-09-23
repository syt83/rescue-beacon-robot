#!/usr/bin/env python3
"""Safe USB check: only sends HELLO, zero motor commands, and optional BEEP."""

import argparse
import sys
import time

import serial


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', default='/dev/ttyACM0')
    parser.add_argument('--timeout', type=float, default=8.0)
    parser.add_argument(
        '--beep', action='store_true',
        help='forward one playback request to DFPlayer Mini',
    )
    args = parser.parse_args()

    try:
        board = serial.Serial(
            args.port, 115200, timeout=0.25,
            write_timeout=0.5, exclusive=True,
        )
    except serial.SerialException as exc:
        print(f'Cannot open {args.port}: {exc}', file=sys.stderr)
        return 2

    seen = set()
    ready = False
    last_hello = 0.0
    deadline = time.monotonic() + args.timeout
    required = {'ENC', 'SOUND'}
    if args.beep:
        required.add('BEEP')
    try:
        while time.monotonic() < deadline:
            now = time.monotonic()
            if not ready and now - last_hello >= 0.5:
                board.write(b'HELLO\n')
                last_hello = now
            raw = board.readline()
            if not raw:
                continue
            line = raw.decode('utf-8', 'replace').strip()
            if not line:
                continue
            if line == 'READY,1' and not ready:
                ready = True
                print('READY,1: matching rescue_beacon_firmware')
                board.write(b'CMD,0.000,0.000\n')
                if args.beep:
                    board.write(b'BEEP,1\n')
                continue
            if line.startswith('ENC,') and 'ENC' not in seen:
                print(line)
                seen.add('ENC')
            elif line.startswith('SOUND,') and 'SOUND' not in seen:
                print(line)
                seen.add('SOUND')
            elif line == 'ACK,BEEP':
                print(line + ' (command forwarded; verify sound by ear)')
                seen.add('BEEP')
            elif not ready and 'OTHER' not in seen:
                print(f'Other firmware output: {line}')
                seen.add('OTHER')

            if ready and required <= seen:
                return 0
    finally:
        if ready:
            try:
                board.write(b'CMD,0.000,0.000\n')
            except serial.SerialException:
                pass
        board.close()

    if not ready:
        print('No READY,1: upload the repository firmware first.', file=sys.stderr)
    else:
        print(f'Missing telemetry: {sorted(required - seen)}', file=sys.stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
