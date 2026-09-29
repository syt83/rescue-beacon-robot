#!/usr/bin/env python3
"""Run a bounded floor approach toward a person and stop after ALERT."""

import sys

from run_integrated_stand_test import main


if __name__ == '__main__':
    main(['--floor', '--until-alert', '--seconds', '8', *sys.argv[1:]])
