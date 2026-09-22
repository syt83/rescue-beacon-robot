import math

import rclpy
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
                    values.append(distance)
        return min(values) if values else float('inf')

    def scan_callback(self, msg):
        front = self.sector_min(msg, -20.0, 20.0)
        left = self.sector_min(msg, 20.0, 85.0)
        right = self.sector_min(msg, -85.0, -20.0)

        cmd = Twist()

        if front < self.stop_distance:
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
