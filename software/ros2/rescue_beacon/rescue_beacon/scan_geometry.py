"""Read LiDAR sectors in robot coordinates, including the mounting yaw."""

import math


def sector_min(scan, start_deg, end_deg, scan_yaw_offset_deg=0.0):
    """Return the nearest valid reading between robot-relative angles."""
    nearest = float('inf')
    for index, distance in enumerate(scan.ranges):
        if not (
            math.isfinite(distance)
            and scan.range_min < distance < scan.range_max
        ):
            continue
        laser_angle_deg = math.degrees(
            scan.angle_min + index * scan.angle_increment
        )
        robot_angle_deg = (
            laser_angle_deg - scan_yaw_offset_deg + 180.0
        ) % 360.0 - 180.0
        if start_deg <= robot_angle_deg <= end_deg:
            nearest = min(nearest, distance)
    return nearest
