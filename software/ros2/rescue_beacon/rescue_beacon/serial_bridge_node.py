import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import Bool

try:
    import serial
except ImportError:
    serial = None


class SerialBridgeNode(Node):
    """Single owner of the Arduino USB serial port."""

    def __init__(self):
        super().__init__('serial_bridge_node')

        if serial is None:
            raise RuntimeError(
                'pyserial is not installed. Install python3-serial or pyserial.'
            )

        self.declare_parameter('port', '/dev/ttyACM0')
        self.declare_parameter('baud', 115200)
        self.declare_parameter('cmd_topic', '/cmd_vel')
        self.declare_parameter('beacon_topic', '/beacon_trigger')
        self.declare_parameter('send_rate_hz', 20.0)
        self.declare_parameter('reconnect_sec', 2.0)

        self.port = str(self.get_parameter('port').value)
        self.baud = int(self.get_parameter('baud').value)
        self.send_rate_hz = float(self.get_parameter('send_rate_hz').value)
        self.reconnect_sec = float(self.get_parameter('reconnect_sec').value)

        self.ser = None
        self.last_reconnect_attempt = 0.0
        self.latest_cmd = Twist()
        self.beacon_state = False

        self.create_subscription(
            Twist,
            self.get_parameter('cmd_topic').value,
            self.cmd_cb,
            10,
        )
        self.create_subscription(
            Bool,
            self.get_parameter('beacon_topic').value,
            self.beacon_cb,
            10,
        )

        period = 1.0 / max(self.send_rate_hz, 1.0)
        self.timer = self.create_timer(period, self.timer_cb)

        self.get_logger().info(
            f'Serial bridge started: {self.port} @ {self.baud}'
        )

    def ensure_serial(self):
        if self.ser is not None and self.ser.is_open:
            return True

        now = time.monotonic()
        if now - self.last_reconnect_attempt < self.reconnect_sec:
            return False
        self.last_reconnect_attempt = now

        try:
            self.ser = serial.Serial(
                self.port,
                self.baud,
                timeout=0.0,
                write_timeout=0.05,
            )
            self.get_logger().info(f'Connected to Arduino: {self.port}')
            return True
        except Exception as exc:
            self.get_logger().warning(
                f'Arduino serial unavailable ({self.port}): {exc}'
            )
            self.ser = None
            return False

    def send_line(self, text):
        if not self.ensure_serial():
            return False
        try:
            self.ser.write((text + '\n').encode('ascii'))
            return True
        except Exception as exc:
            self.get_logger().error(f'Serial write failed: {exc}')
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None
            return False

    def cmd_cb(self, msg):
        self.latest_cmd = msg

    def beacon_cb(self, msg):
        new_state = bool(msg.data)
        if new_state and not self.beacon_state:
            self.send_line('BEEP,1')
        self.beacon_state = new_state

    def timer_cb(self):
        self.send_line(
            f'CMD,{self.latest_cmd.linear.x:.3f},'
            f'{self.latest_cmd.angular.z:.3f}'
        )

        if self.ser is not None and self.ser.is_open:
            try:
                while self.ser.in_waiting:
                    line = self.ser.readline().decode(
                        'utf-8', errors='replace'
                    ).strip()
                    if line:
                        self.get_logger().debug(f'Arduino: {line}')
            except Exception:
                pass

    def destroy_node(self):
        try:
            self.send_line('CMD,0.000,0.000')
        except Exception:
            pass
        if self.ser is not None:
            try:
                self.ser.close()
            except Exception:
                pass
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = SerialBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
