import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import Bool

try:
    from ai_msgs.msg import PerceptionTargets
except ImportError:
    PerceptionTargets = None


def clamp(value, low, high):
    return max(low, min(high, value))


class PersonFollowNode(Node):
    """
    Converts D-Robotics mono2d body detections into a simple person approach command.

    Distance is NOT metric here. The body bounding-box height ratio is used only as
    a near/far proxy. Metric stereo depth can replace this proxy later without
    changing the mission-controller interface.
    """

    def __init__(self):
        super().__init__('person_follow_node')

        if PerceptionTargets is None:
            raise RuntimeError(
                'ai_msgs is not available. Run this node on RDK/TROS with '
                'D-Robotics perception packages installed.'
            )

        self.declare_parameter(
            'detection_topic', '/hobot_mono2d_body_detection'
        )
        self.declare_parameter('cmd_topic', '/person_cmd_vel')
        self.declare_parameter('detected_topic', '/person_detected')
        self.declare_parameter('close_topic', '/person_close')
        self.declare_parameter('image_width', 960.0)
        self.declare_parameter('image_height', 544.0)
        self.declare_parameter('angular_kp', 0.85)
        self.declare_parameter('max_angular', 0.55)
        self.declare_parameter('max_linear', 0.14)
        self.declare_parameter('min_linear', 0.04)
        self.declare_parameter('stop_height_ratio', 0.72)
        self.declare_parameter('rotate_only_error', 0.40)
        self.declare_parameter('lost_timeout_sec', 0.7)

        detection_topic = self.get_parameter('detection_topic').value
        cmd_topic = self.get_parameter('cmd_topic').value
        detected_topic = self.get_parameter('detected_topic').value
        close_topic = self.get_parameter('close_topic').value

        self.image_width = float(self.get_parameter('image_width').value)
        self.image_height = float(self.get_parameter('image_height').value)
        self.angular_kp = float(self.get_parameter('angular_kp').value)
        self.max_angular = float(self.get_parameter('max_angular').value)
        self.max_linear = float(self.get_parameter('max_linear').value)
        self.min_linear = float(self.get_parameter('min_linear').value)
        self.stop_height_ratio = float(
            self.get_parameter('stop_height_ratio').value
        )
        self.rotate_only_error = float(
            self.get_parameter('rotate_only_error').value
        )
        self.lost_timeout_sec = float(
            self.get_parameter('lost_timeout_sec').value
        )

        self.cmd_pub = self.create_publisher(Twist, cmd_topic, 10)
        self.detected_pub = self.create_publisher(Bool, detected_topic, 10)
        self.close_pub = self.create_publisher(Bool, close_topic, 10)

        self.sub = self.create_subscription(
            PerceptionTargets,
            detection_topic,
            self.detection_callback,
            10,
        )

        self.last_detection_time = 0.0
        self.last_seen = False
        self.watchdog = self.create_timer(0.1, self.watchdog_callback)

        self.get_logger().info(
            f'Person follow node started: {detection_topic}'
        )

    @staticmethod
    def get_body_roi(target):
        if not getattr(target, 'rois', None):
            return None

        body_rois = [
            roi for roi in target.rois
            if getattr(roi, 'type', '').lower() in ('body', 'person')
        ]
        candidates = body_rois if body_rois else list(target.rois)
        if not candidates:
            return None

        return max(
            candidates,
            key=lambda roi: float(roi.rect.width) * float(roi.rect.height),
        )

    def detection_callback(self, msg):
        candidates = []

        for target in msg.targets:
            if getattr(target, 'type', '').lower() != 'person':
                continue

            roi = self.get_body_roi(target)
            if roi is None:
                continue

            area = float(roi.rect.width) * float(roi.rect.height)
            candidates.append((area, roi))

        if not candidates:
            self.publish_lost()
            return

        _, roi = max(candidates, key=lambda item: item[0])
        rect = roi.rect

        center_x = float(rect.x_offset) + float(rect.width) * 0.5
        center_error = (
            center_x - self.image_width * 0.5
        ) / (self.image_width * 0.5)
        center_error = clamp(center_error, -1.0, 1.0)

        height_ratio = float(rect.height) / max(self.image_height, 1.0)
        close = height_ratio >= self.stop_height_ratio

        cmd = Twist()
        cmd.angular.z = clamp(
            -self.angular_kp * center_error,
            -self.max_angular,
            self.max_angular,
        )

        if close:
            cmd.linear.x = 0.0
        elif abs(center_error) > self.rotate_only_error:
            cmd.linear.x = 0.0
        else:
            scale = 1.0 - (height_ratio / max(self.stop_height_ratio, 0.01))
            cmd.linear.x = clamp(
                self.max_linear * scale,
                self.min_linear,
                self.max_linear,
            )

        self.cmd_pub.publish(cmd)
        self.detected_pub.publish(Bool(data=True))
        self.close_pub.publish(Bool(data=close))

        self.last_detection_time = time.monotonic()
        self.last_seen = True

    def publish_lost(self):
        self.cmd_pub.publish(Twist())
        self.detected_pub.publish(Bool(data=False))
        self.close_pub.publish(Bool(data=False))
        self.last_seen = False

    def watchdog_callback(self):
        if (
            self.last_seen
            and time.monotonic() - self.last_detection_time
            > self.lost_timeout_sec
        ):
            self.publish_lost()


def main(args=None):
    rclpy.init(args=args)
    node = PersonFollowNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.cmd_pub.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
