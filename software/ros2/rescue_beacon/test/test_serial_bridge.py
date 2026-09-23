"""Exercise the real pyserial bridge against a pseudo Arduino USB port."""

import os
import pty
import sys
import time
import unittest
from pathlib import Path

import rclpy
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rescue_beacon.serial_bridge_node import SerialBridgeNode  # noqa: E402


class SerialBridgeSafetyTest(unittest.TestCase):
    def setUp(self):
        self.master_fd, self.slave_fd = pty.openpty()
        self.port = os.ttyname(self.slave_fd)
        os.set_blocking(self.master_fd, False)
        rclpy.init(args=[
            '--ros-args',
            '-p', f'port:={self.port}',
            '-p', 'reconnect_sec:=0.1',
        ])
        self.node = SerialBridgeNode()

    def tearDown(self):
        self.node.destroy_node()
        rclpy.shutdown()
        os.close(self.master_fd)
        os.close(self.slave_fd)

    def read_commands(self):
        time.sleep(0.02)
        chunks = []
        while True:
            try:
                chunks.append(os.read(self.master_fd, 4096))
            except BlockingIOError:
                break
        return b''.join(chunks).decode('ascii', 'replace')

    def write_reply(self, text):
        os.write(self.master_fd, text.encode('ascii'))

    def test_handshake_motion_gate_timeout_and_beacon(self):
        moving = Twist()
        moving.linear.x = 0.05
        self.node.cmd_cb(moving)
        self.node.timer_cb()
        self.assertIn('HELLO\n', self.read_commands())

        self.write_reply('Nano Every Ready\n')
        self.node.timer_cb()
        self.assertFalse(self.node.ready)
        self.assertNotIn('CMD,', self.read_commands())

        self.write_reply('REA')
        self.node.timer_cb()
        self.assertFalse(self.node.ready)
        self.write_reply('DY,1\n')
        self.node.timer_cb()
        self.assertTrue(self.node.ready)
        self.assertIn('CMD,0.000,0.000\n', self.read_commands())

        self.node.cmd_cb(moving)
        self.node.timer_cb()
        self.assertIn('CMD,0.000,0.000\n', self.read_commands())

        self.node.enable_motion = True
        self.node.timer_cb()
        self.assertIn('CMD,0.050,0.000\n', self.read_commands())

        self.node.last_cmd_time = time.monotonic() - 1.0
        self.node.timer_cb()
        self.assertIn('CMD,0.000,0.000\n', self.read_commands())

        self.node.beacon_cb(Bool(data=True))
        self.node.timer_cb()
        self.assertIn('BEEP,1\n', self.read_commands())
        self.node.timer_cb()
        self.assertNotIn('BEEP,1\n', self.read_commands())

        self.node.disconnect()
        self.node.last_reconnect_attempt = 0.0
        self.node.timer_cb()
        self.assertIn('HELLO\n', self.read_commands())
        self.write_reply('READY,1\n')
        self.node.timer_cb()
        self.assertIn('BEEP,1\n', self.read_commands())


if __name__ == '__main__':
    unittest.main()
