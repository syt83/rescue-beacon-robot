#!/usr/bin/env python3
"""Run the bounded full-mission trial on a clear floor (maximum 2 seconds)."""

import sys

from run_integrated_stand_test import main


if __name__ == '__main__':
    main(['--floor', *sys.argv[1:]])
