#!/usr/bin/env python3
"""Print one LiDAR scan's usable distances without starting any motor nodes."""

import math
from pathlib import Path
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan, PointCloud

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'software/ros2/rescue_beacon'))
from rescue_beacon.scan_geometry import sector_min  # noqa: E402


def main():
    rclpy.init()
    node = Node('rescue_scan_check')
    received = []
    point_clouds = []
    node.create_subscription(
        LaserScan, '/scan', lambda message: received.append(message),
        qos_profile_sensor_data,
    )
    node.create_subscription(
        PointCloud, '/point_cloud',
        lambda message: point_clouds.append(message),
        qos_profile_sensor_data,
    )
    try:
        deadline = time.monotonic() + 6.0
        while (len(received) < 10 or len(point_clouds) < 10) and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.2)
        if not received:
            print('/scan 메시지를 6초 동안 받지 못했습니다.')
            return 1

        scan = received[-1]
        valid_counts = [
            sum(
                math.isfinite(distance)
                and item.range_min < distance < item.range_max
                for distance in item.ranges
            )
            for item in received
        ]
        print(f'{len(received)}회 스캔의 유효 거리 수: {valid_counts}')
        fronts = [
            sector_min(item, -18.0, 18.0, 180.0)
            for item in received
        ]
        print(
            '정면 거리 기록: '
            + ', '.join(
                f'{distance:.2f}m' if math.isfinite(distance) else '없음'
                for distance in fronts
            )
        )
        if point_clouds:
            print(
                f'{len(point_clouds)}회 원시 점 수: '
                f'{[len(cloud.points) for cloud in point_clouds]}'
            )
        else:
            print('/point_cloud 메시지를 받지 못했습니다.')
        valid = [
            distance for distance in scan.ranges
            if math.isfinite(distance)
            and scan.range_min < distance < scan.range_max
        ]
        print(
            f'전체 측정값: {len(scan.ranges)}, 유효한 거리: {len(valid)}, '
            f'허용 범위: {scan.range_min:.2f}~{scan.range_max:.2f} m'
        )
        zero = sum(distance == 0.0 for distance in scan.ranges)
        infinite = sum(math.isinf(distance) for distance in scan.ranges)
        nan = sum(math.isnan(distance) for distance in scan.ranges)
        below = sum(
            math.isfinite(distance) and 0.0 < distance <= scan.range_min
            for distance in scan.ranges
        )
        above = sum(
            math.isfinite(distance) and distance >= scan.range_max
            for distance in scan.ranges
        )
        print(
            f'0값: {zero}, 무한대: {infinite}, NaN: {nan}, '
            f'최소범위 이하: {below}, 최대범위 이상: {above}'
        )
        print(
            f'스캔 각도: {math.degrees(scan.angle_min):.1f}~'
            f'{math.degrees(scan.angle_max):.1f}도, '
            f'간격: {math.degrees(scan.angle_increment):.3f}도'
        )
        nearest = []
        for index, distance in enumerate(scan.ranges):
            if not (
                math.isfinite(distance)
                and scan.range_min < distance < scan.range_max
            ):
                continue
            raw_angle = math.degrees(
                scan.angle_min + index * scan.angle_increment
            )
            robot_angle = (raw_angle - 180.0 + 180.0) % 360.0 - 180.0
            nearest.append((distance, raw_angle, robot_angle))
        for distance, raw_angle, robot_angle in sorted(nearest)[:8]:
            print(
                f'가까운 점: {distance:.2f} m, '
                f'센서 각도 {raw_angle:+.0f}도, '
                f'로봇 각도 {robot_angle:+.0f}도'
            )
        for name, start, end in (
            ('정면', -18.0, 18.0),
            ('왼쪽', 18.0, 85.0),
            ('오른쪽', -85.0, -18.0),
        ):
            distance = sector_min(scan, start, end, 180.0)
            value = f'{distance:.2f} m' if math.isfinite(distance) else '유효한 값 없음'
            print(f'{name}: {value}')
        return 0
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
