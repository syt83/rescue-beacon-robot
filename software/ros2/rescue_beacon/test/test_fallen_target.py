"""Ensure the camera trial cannot drive toward standing or sitting detections."""

import sys
import unittest
from pathlib import Path

import rclpy
from ai_msgs.msg import PerceptionTargets, Roi, Target

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rescue_beacon.person_follow_node import PersonFollowNode  # noqa: E402


class Recorder:
    def __init__(self):
        self.messages = []

    def publish(self, message):
        self.messages.append(message)


def detection(label):
    message = PerceptionTargets()
    target = Target()
    target.type = label
    roi = Roi()
    roi.type = 'body'
    roi.confidence = 0.8
    roi.rect.x_offset = 800
    roi.rect.y_offset = 200
    roi.rect.width = 320
    roi.rect.height = 400
    target.rois.append(roi)
    message.targets.append(target)
    return message


class FallenTargetTest(unittest.TestCase):
    def test_only_fallen_causes_approach(self):
        rclpy.init(args=[
            '--ros-args',
            '-p', 'require_fallen:=true',
            '-p', 'image_width:=1920.0',
            '-p', 'image_height:=1080.0',
        ])
        node = PersonFollowNode()
        node.cmd_pub = Recorder()
        node.detected_pub = Recorder()
        node.close_pub = Recorder()
        try:
            for label in ('standing', 'sit'):
                node.detection_callback(detection(label))
                self.assertFalse(node.detected_pub.messages[-1].data)
                self.assertEqual(node.cmd_pub.messages[-1].linear.x, 0.0)

            node.detection_callback(detection('fallen'))
            self.assertTrue(node.detected_pub.messages[-1].data)
            self.assertGreater(node.cmd_pub.messages[-1].linear.x, 0.0)
        finally:
            node.destroy_node()
            rclpy.shutdown()


if __name__ == '__main__':
    unittest.main()
