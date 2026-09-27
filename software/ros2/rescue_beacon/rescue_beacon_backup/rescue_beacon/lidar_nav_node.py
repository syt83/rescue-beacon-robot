import math

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist


class LidarNavNode(Node):

    def __init__(self):
        super().__init__('lidar_nav_node')

        self.scan_sub = self.create_subscription(
            LaserScan,
            '/scan',
            self.scan_callback,
            qos_profile_sensor_data
        )

        self.cmd_pub = self.create_publisher(
            Twist,
            '/cmd_vel',
            10
        )

        self.stop_distance = 0.40
        self.warning_distance = 0.70

        self.scan_count = 0

        self.get_logger().info(
            'LiDAR navigation node started.'
        )

    def get_sector_min(self, msg, start_deg, end_deg):
        valid_ranges = []

        for i, distance in enumerate(msg.ranges):

            angle = msg.angle_min + i * msg.angle_increment
            angle_deg = math.degrees(angle)

            if start_deg <= angle_deg <= end_deg:

                if (
                    math.isfinite(distance)
                    and msg.range_min < distance < msg.range_max
                ):
                    valid_ranges.append(distance)

        if not valid_ranges:
            return float('inf')

        return min(valid_ranges)

    def scan_callback(self, msg):

        front = self.get_sector_min(msg, -20, 20)
        left = self.get_sector_min(msg, 20, 80)
        right = self.get_sector_min(msg, -80, -20)

        cmd = Twist()

        if front < self.stop_distance:

            cmd.linear.x = 0.0

            if left > right:
                cmd.angular.z = 0.5
            else:
                cmd.angular.z = -0.5

        elif front < self.warning_distance:

            cmd.linear.x = 0.08

            if left > right:
                cmd.angular.z = 0.25
            else:
                cmd.angular.z = -0.25

        else:

            cmd.linear.x = 0.15
            cmd.angular.z = 0.0

        self.cmd_pub.publish(cmd)

        self.scan_count += 1

        if self.scan_count >= 10:

            self.get_logger().info(
                f'Front: {front:.2f} m | '
                f'Left: {left:.2f} m | '
                f'Right: {right:.2f} m | '
                f'v: {cmd.linear.x:.2f} m/s | '
                f'w: {cmd.angular.z:.2f} rad/s'
            )

            self.scan_count = 0


def main(args=None):

    rclpy.init(args=args)

    node = LidarNavNode()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        stop_cmd = Twist()
        node.cmd_pub.publish(stop_cmd)

        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()