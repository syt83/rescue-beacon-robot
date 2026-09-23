import math

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist


class LidarNavNode(Node):
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan


def clamp(value, low, high):
    return max(low, min(high, value))


class LidarNavNode(Node):
    """Simple mapping-free search / obstacle-avoidance command generator."""

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

        self.declare_parameter('scan_topic', '/scan')
        self.declare_parameter('output_topic', '/search_cmd_vel')
        self.declare_parameter('stop_distance', 0.40)
        self.declare_parameter('warning_distance', 0.70)
        self.declare_parameter('search_speed', 0.14)
        self.declare_parameter('slow_speed', 0.06)
        self.declare_parameter('turn_speed', 0.45)
        self.declare_parameter('slow_turn_speed', 0.25)

        scan_topic = self.get_parameter('scan_topic').value
        output_topic = self.get_parameter('output_topic').value

        self.stop_distance = float(self.get_parameter('stop_distance').value)
        self.warning_distance = float(self.get_parameter('warning_distance').value)
        self.search_speed = float(self.get_parameter('search_speed').value)
        self.slow_speed = float(self.get_parameter('slow_speed').value)
        self.turn_speed = float(self.get_parameter('turn_speed').value)
        self.slow_turn_speed = float(self.get_parameter('slow_turn_speed').value)

        self.pub = self.create_publisher(Twist, output_topic, 10)
        self.sub = self.create_subscription(
            LaserScan, scan_topic, self.scan_callback, qos_profile_sensor_data
        )

        self.log_count = 0
        self.get_logger().info(
            f'LiDAR search node started: {scan_topic} -> {output_topic}'
        )

    @staticmethod
    def sector_min(msg, start_deg, end_deg):
        values = []
        for i, distance in enumerate(msg.ranges):
            angle_deg = math.degrees(msg.angle_min + i * msg.angle_increment)
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
                    values.append(distance)
        return min(values) if values else float('inf')

    def scan_callback(self, msg):
        front = self.sector_min(msg, -20.0, 20.0)
        left = self.sector_min(msg, 20.0, 85.0)
        right = self.sector_min(msg, -85.0, -20.0)

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

            cmd.linear.x = 0.0
            cmd.angular.z = self.turn_speed if left >= right else -self.turn_speed
        elif front < self.warning_distance:
            cmd.linear.x = self.slow_speed
            cmd.angular.z = (
                self.slow_turn_speed if left >= right else -self.slow_turn_speed
            )
        else:
            cmd.linear.x = self.search_speed
            # Gentle bias toward the more open side only if strongly asymmetric.
            diff = left - right
            if math.isfinite(diff) and abs(diff) > 0.7:
                cmd.angular.z = clamp(0.12 if diff > 0 else -0.12, -0.12, 0.12)

        self.pub.publish(cmd)

        self.log_count += 1
        if self.log_count >= 20:
            self.get_logger().info(
                f'front={front:.2f} left={left:.2f} right={right:.2f} '
                f'v={cmd.linear.x:.2f} w={cmd.angular.z:.2f}'
            )
            self.log_count = 0


def main(args=None):
    rclpy.init(args=args)
    node = LidarNavNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.pub.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
    main()
