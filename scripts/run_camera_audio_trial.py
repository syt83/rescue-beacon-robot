#!/usr/bin/env python3
"""Run one supervised slow fallen-person approach with audio at ALERT."""

from run_integrated_stand_test import main


if __name__ == '__main__':
    main([
        '--floor', '--camera-only', '--slow', '--audio-on-alert',
        '--until-alert', '--seconds', '30',
    ])
