import math
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool, String


class MissionControllerNode(Node):
    """
    SEARCH -> CONFIRM -> APPROACH -> ALERT state machine.

    It also acts as the safety arbiter. Only this node publishes the final /cmd_vel.
    """

    SEARCH = 'SEARCH'
    CONFIRM = 'CONFIRM'
    APPROACH = 'APPROACH'
    ALERT = 'ALERT'

    def __init__(self):
        super().__init__('mission_controller_node')

        self.declare_parameter('search_cmd_topic', '/search_cmd_vel')
        self.declare_parameter('person_cmd_topic', '/person_cmd_vel')
        self.declare_parameter('person_detected_topic', '/person_detected')
        self.declare_parameter('person_close_topic', '/person_close')
        self.declare_parameter('scan_topic', '/scan')
        self.declare_parameter('output_topic', '/cmd_vel')
        self.declare_parameter('beacon_topic', '/beacon_trigger')
        self.declare_parameter('state_topic', '/mission_state')
        self.declare_parameter('confirm_cycles', 3)
        self.declare_parameter('lost_cycles', 8)
        self.declare_parameter('emergency_stop_distance', 0.25)
        self.declare_parameter('caution_distance', 0.45)
        self.declare_parameter('avoid_turn_speed', 0.45)
        self.declare_parameter('scan_timeout_sec', 1.0)
        self.declare_parameter('input_timeout_sec', 0.5)

        p = lambda name: self.get_parameter(name).value

        self.confirm_cycles = int(p('confirm_cycles'))
        self.lost_cycles_limit = int(p('lost_cycles'))
        self.emergency_stop_distance = float(p('emergency_stop_distance'))
        self.caution_distance = float(p('caution_distance'))
        self.avoid_turn_speed = float(p('avoid_turn_speed'))
        self.scan_timeout_sec = float(p('scan_timeout_sec'))
        self.input_timeout_sec = float(p('input_timeout_sec'))

        self.final_pub = self.create_publisher(Twist, p('output_topic'), 10)
        self.beacon_pub = self.create_publisher(Bool, p('beacon_topic'), 10)
        self.state_pub = self.create_publisher(String, p('state_topic'), 10)

        self.create_subscription(
            Twist, p('search_cmd_topic'), self.search_cmd_cb, 10
        )
        self.create_subscription(
            Twist, p('person_cmd_topic'), self.person_cmd_cb, 10
        )
        self.create_subscription(
            Bool, p('person_detected_topic'), self.person_detected_cb, 10
        )
        self.create_subscription(
            Bool, p('person_close_topic'), self.person_close_cb, 10
        )
        self.create_subscription(
            LaserScan, p('scan_topic'), self.scan_cb, qos_profile_sensor_data
        )

        self.search_cmd = Twist()
        self.person_cmd = Twist()
        self.person_detected = False
        self.person_close = False
        self.last_search_cmd_time = 0.0
        self.last_person_cmd_time = 0.0
        self.last_person_detection_time = 0.0
        self.last_person_close_time = 0.0

        self.front = float('inf')
        self.left = float('inf')
        self.right = float('inf')
        self.last_scan_time = 0.0

        self.state = self.SEARCH
        self.confirm_count = 0
        self.lost_count = 0
        self.beacon_active = False

        self.timer = self.create_timer(0.1, self.control_tick)
        self.get_logger().info('Mission controller started.')

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

    @staticmethod
    def copy_twist(src):
        dst = Twist()
        dst.linear.x = src.linear.x
        dst.linear.y = src.linear.y
        dst.linear.z = src.linear.z
        dst.angular.x = src.angular.x
        dst.angular.y = src.angular.y
        dst.angular.z = src.angular.z
        return dst

    def search_cmd_cb(self, msg):
        self.search_cmd = msg
        self.last_search_cmd_time = time.monotonic()

    def person_cmd_cb(self, msg):
        self.person_cmd = msg
        self.last_person_cmd_time = time.monotonic()

    def person_detected_cb(self, msg):
        self.person_detected = bool(msg.data)
        self.last_person_detection_time = time.monotonic()

    def person_close_cb(self, msg):
        self.person_close = bool(msg.data)
        self.last_person_close_time = time.monotonic()

    def scan_cb(self, msg):
        self.front = self.sector_min(msg, -18.0, 18.0)
        self.left = self.sector_min(msg, 18.0, 85.0)
        self.right = self.sector_min(msg, -85.0, -18.0)
        self.last_scan_time = time.monotonic()

    def set_state(self, new_state):
        if new_state != self.state:
            self.get_logger().info(f'STATE {self.state} -> {new_state}')
            self.state = new_state

    @staticmethod
    def is_fresh(last_time, timeout_sec, now):
        return last_time > 0.0 and now - last_time <= timeout_sec

    def update_state(self):
        # A confirmed rescue target ends this search run. Do not drive again
        # if the camera briefly loses the target at close range.
        if self.state == self.ALERT:
            return

        if self.person_detected:
            self.lost_count = 0
            if self.state == self.SEARCH:
                self.set_state(self.CONFIRM)
                self.confirm_count = 1
            elif self.state == self.CONFIRM:
                self.confirm_count += 1
                if self.confirm_count >= self.confirm_cycles:
                    self.set_state(self.APPROACH)
            elif self.state == self.APPROACH and self.person_close:
                self.set_state(self.ALERT)
        else:
            self.confirm_count = 0
            self.lost_count += 1
            if self.lost_count >= self.lost_cycles_limit:
                self.set_state(self.SEARCH)

    def safety_filter(self, cmd):
        out = self.copy_twist(cmd)

        # No recent or valid front scan means no movement.
        if (
            self.last_scan_time == 0.0
            or time.monotonic() - self.last_scan_time > self.scan_timeout_sec
            or not math.isfinite(self.front)
        ):
            out.linear.x = 0.0
            out.angular.z = 0.0
            return out

        if self.front < self.emergency_stop_distance:
            out.linear.x = 0.0
            if self.state != self.ALERT and (
                cmd.linear.x != 0.0 or cmd.angular.z != 0.0
            ):
                out.angular.z = (
                    self.avoid_turn_speed
                    if self.left >= self.right
                    else -self.avoid_turn_speed
                )
            else:
                out.angular.z = 0.0
            return out

        if self.front < self.caution_distance and out.linear.x > 0.0:
            out.linear.x = min(out.linear.x, 0.04)
            if abs(out.angular.z) < 0.1:
                out.angular.z = (
                    0.20 if self.left >= self.right else -0.20
                )

        return out

    def control_tick(self):
        now = time.monotonic()
        if not self.is_fresh(
            self.last_person_detection_time, self.input_timeout_sec, now
        ):
            self.person_detected = False
        if not self.person_detected or not self.is_fresh(
            self.last_person_close_time, self.input_timeout_sec, now
        ):
            self.person_close = False

        self.update_state()

        if self.state == self.SEARCH:
            requested = (
                self.search_cmd
                if self.is_fresh(
                    self.last_search_cmd_time, self.input_timeout_sec, now
                ) else Twist()
            )
        elif self.state == self.CONFIRM:
            requested = Twist()
        elif self.state == self.APPROACH:
            requested = (
                self.person_cmd
                if self.person_detected and self.is_fresh(
                    self.last_person_cmd_time, self.input_timeout_sec, now
                ) else Twist()
            )
        else:  # ALERT
            requested = Twist()

        final_cmd = self.safety_filter(requested)
        self.final_pub.publish(final_cmd)

        should_beep = self.state == self.ALERT
        self.beacon_active = should_beep
        # Publish the level continuously so a reconnected bridge also sees
        # an ALERT that began before its subscription was ready.
        self.beacon_pub.publish(Bool(data=should_beep))

        self.state_pub.publish(String(data=self.state))


def main(args=None):
    rclpy.init(args=args)
    node = MissionControllerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.final_pub.publish(Twist())
        node.beacon_pub.publish(Bool(data=False))
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
