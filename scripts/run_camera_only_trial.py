#!/usr/bin/env python3
"""Run one supervised, slow, silent, two-second camera-only approach trial."""

from run_integrated_stand_test import main


if __name__ == '__main__':
    main(['--floor', '--camera-only', '--slow', '--no-audio', '--seconds', '2'])
