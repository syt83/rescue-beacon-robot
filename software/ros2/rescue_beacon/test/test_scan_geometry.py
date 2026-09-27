"""The mounted LiDAR reports robot-forward objects near raw 180 degrees."""

import math
import sys
import unittest
from pathlib import Path

from sensor_msgs.msg import LaserScan

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rescue_beacon.scan_geometry import sector_min  # noqa: E402


class ScanGeometryTest(unittest.TestCase):
    def test_rear_facing_lidar_maps_forward_and_sides(self):
        scan = LaserScan()
        scan.angle_min = -math.pi
        scan.angle_increment = math.pi / 180
        scan.range_min = 0.10
        scan.range_max = 12.0
        scan.ranges = [float('inf')] * 361
        scan.ranges[353] = 0.43  # raw +173 degrees: robot front
        scan.ranges[90] = 1.0   # raw -90 degrees: robot left
        scan.ranges[270] = 2.0  # raw +90 degrees: robot right

        self.assertTrue(math.isinf(sector_min(scan, -20, 20)))
        self.assertAlmostEqual(sector_min(scan, -20, 20, 180), 0.43)
        self.assertAlmostEqual(sector_min(scan, 85, 95, 180), 1.0)
        self.assertAlmostEqual(sector_min(scan, -95, -85, 180), 2.0)


if __name__ == '__main__':
    unittest.main()
