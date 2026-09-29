"""Check that the model's posture labels survive conversion to ROS messages."""

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

from builtin_interfaces.msg import Time


class YoloBridgeLabelTest(unittest.TestCase):
    def test_fallen_sit_standing_are_preserved(self):
        fake_runtime = types.ModuleType('ros_yolo_live')
        fake_runtime.CLASS_NAMES = ['fallen', 'sit', 'standing']
        fake_runtime.RescueYoloNode = object
        path = Path(__file__).with_name('ros_yolo_bridge.py')
        with patch.dict(sys.modules, {'ros_yolo_live': fake_runtime}):
            spec = importlib.util.spec_from_file_location('bridge_under_test', path)
            bridge = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bridge)

        message = bridge.build_perception_message(
            [(10, 20, 100, 200)] * 3,
            [0.8] * 3,
            [0, 1, 2],
            1920,
            1080,
            Time(),
        )
        self.assertEqual(
            [target.type for target in message.targets],
            ['fallen', 'sit', 'standing'],
        )


if __name__ == '__main__':
    unittest.main()
