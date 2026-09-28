"""Regression checks for the final motor and alert outputs."""

import sys
import time
import unittest
from pathlib import Path

import rclpy
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rescue_beacon.mission_controller_node import MissionControllerNode  # noqa: E402


class Recorder:
    def __init__(self):
        self.messages = []

    def publish(self, message):
        self.messages.append(message)


class MissionSafetyTest(unittest.TestCase):
    def setUp(self):
        rclpy.init()
        self.node = MissionControllerNode()
        self.final = Recorder()
        self.beacon = Recorder()
        self.state = Recorder()
        self.node.final_pub = self.final
        self.node.beacon_pub = self.beacon
        self.node.state_pub = self.state

    def tearDown(self):
        self.node.destroy_node()
        rclpy.shutdown()

    def test_alert_stays_stopped_after_target_disappears(self):
        self.node.state = self.node.ALERT
        self.node.front = 2.0
        self.node.last_scan_time = time.monotonic()
        self.node.person_detected = False
        self.node.control_tick()
        self.node.control_tick()

        self.assertEqual(self.node.state, self.node.ALERT)
        self.assertEqual(self.final.messages[-1].linear.x, 0.0)
        self.assertEqual(self.final.messages[-1].angular.z, 0.0)
        self.assertTrue(all(message.data for message in self.beacon.messages))

    def test_stale_scan_stops_fresh_search_command(self):
        cmd = Twist()
        cmd.linear.x = 0.14
        self.node.search_cmd_cb(cmd)
        self.node.front = 2.0
        self.node.last_scan_time = (
            time.monotonic() - self.node.scan_timeout_sec - 0.1
        )
        self.node.control_tick()

        self.assertEqual(self.node.state, self.node.SEARCH)
        self.assertEqual(self.final.messages[-1].linear.x, 0.0)
        self.assertEqual(self.final.messages[-1].angular.z, 0.0)
        self.assertFalse(self.beacon.messages[-1].data)

    def test_close_obstacle_stops_forward_and_rotation(self):
        cmd = Twist()
        cmd.linear.x = 0.14
        cmd.angular.z = 0.45
        self.node.search_cmd_cb(cmd)
        self.node.front = 0.43
        self.node.last_scan_time = time.monotonic()
        self.node.control_tick()

        self.assertEqual(self.final.messages[-1].linear.x, 0.0)
        self.assertEqual(self.final.messages[-1].angular.z, 0.0)

    def test_search_only_ignores_person_detections(self):
        self.node.enable_person = False
        self.node.front = 2.0
        self.node.last_scan_time = time.monotonic()
        cmd = Twist()
        cmd.linear.x = 0.05
        self.node.search_cmd_cb(cmd)
        self.node.person_detected_cb(Bool(data=True))
        self.node.person_close_cb(Bool(data=True))
        self.node.control_tick()

        self.assertEqual(self.node.state, self.node.SEARCH)
        self.assertEqual(self.final.messages[-1].linear.x, 0.05)

    def test_camera_only_waits_for_person_then_stops_on_close(self):
        self.node.camera_only = True
        search = Twist()
        search.linear.x = 0.14
        self.node.search_cmd_cb(search)
        self.node.control_tick()
        self.assertEqual(self.final.messages[-1].linear.x, 0.0)

        approach = Twist()
        approach.linear.x = 0.05
        for _ in range(self.node.confirm_cycles):
            self.node.person_detected_cb(Bool(data=True))
            self.node.person_cmd_cb(approach)
            self.node.control_tick()
        self.assertEqual(self.node.state, self.node.APPROACH)
        self.assertEqual(self.final.messages[-1].linear.x, 0.05)

        self.node.person_close_cb(Bool(data=True))
        self.node.control_tick()
        self.assertEqual(self.node.state, self.node.ALERT)
        self.assertEqual(self.final.messages[-1].linear.x, 0.0)
        self.assertEqual(self.final.messages[-1].angular.z, 0.0)


if __name__ == '__main__':
    unittest.main()
