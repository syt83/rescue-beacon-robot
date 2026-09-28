#!/usr/bin/env python3
"""Follow only a YOLO fallen target until visual arrival or 30 seconds."""

from run_integrated_stand_test import main


if __name__ == '__main__':
    main([
        '--floor', '--camera-only', '--slow', '--no-audio',
        '--until-alert', '--seconds', '30',
    ])
