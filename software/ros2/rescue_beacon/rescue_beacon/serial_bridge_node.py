import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import Bool, String

try:
    import serial
except ImportError:
    serial = None


PROTOCOL_READY = 'READY,1'


class SerialBridgeNode(Node):
    """Own the Arduino USB port and require a matching firmware handshake."""

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
        self.declare_parameter('ready_topic', '/arduino_ready')
        self.declare_parameter('telemetry_topic', '/arduino_telemetry')
        self.declare_parameter('sound_topic', '/sound_detected')
        self.declare_parameter('send_rate_hz', 20.0)
        self.declare_parameter('reconnect_sec', 2.0)
        self.declare_parameter('cmd_timeout_sec', 0.5)
        self.declare_parameter('enable_motion', False)

        p = lambda name: self.get_parameter(name).value
        self.port = str(p('port'))
        self.baud = int(p('baud'))
        self.send_rate_hz = float(p('send_rate_hz'))
        self.reconnect_sec = float(p('reconnect_sec'))
        self.cmd_timeout_sec = float(p('cmd_timeout_sec'))
        self.enable_motion = bool(p('enable_motion'))

        self.ser = None
        self.ready = False
        self.recv_buffer = bytearray()
        self.last_reconnect_attempt = 0.0
        self.last_hello_time = 0.0
        self.latest_cmd = Twist()
        self.last_cmd_time = 0.0
        self.beacon_state = False
        self.beep_pending = False

        self.create_subscription(
            Twist, p('cmd_topic'), self.cmd_cb, 10
        )
        self.create_subscription(
            Bool, p('beacon_topic'), self.beacon_cb, 10
        )
        self.ready_pub = self.create_publisher(Bool, p('ready_topic'), 10)
        self.telemetry_pub = self.create_publisher(
            String, p('telemetry_topic'), 10
        )
        self.sound_pub = self.create_publisher(Bool, p('sound_topic'), 10)

        self.timer = self.create_timer(
            1.0 / max(self.send_rate_hz, 1.0), self.timer_cb
        )
        self.get_logger().info(
            f'Serial bridge: {self.port} @ {self.baud}, '
            f'enable_motion={self.enable_motion}'
        )

    def disconnect(self):
        if self.ser is not None:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser = None
        self.ready = False
        self.recv_buffer.clear()
        self.last_cmd_time = 0.0
        self.beep_pending = self.beacon_state

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
                exclusive=True,
            )
            self.ready = False
            self.recv_buffer.clear()
            self.last_cmd_time = 0.0
            self.last_hello_time = 0.0
            self.beep_pending = self.beacon_state
            self.get_logger().info(f'Opened Arduino port: {self.port}')
            return True
        except Exception as exc:
            self.get_logger().warning(
                f'Arduino serial unavailable ({self.port}): {exc}'
            )
            self.ser = None
            return False

    def send_line(self, line):
        if self.ser is None or not self.ser.is_open:
            return False
        try:
            self.ser.write((line + '\n').encode('ascii'))
            return True
        except Exception as exc:
            self.get_logger().error(f'Serial write failed: {exc}')
            self.disconnect()
            return False

    def cmd_cb(self, msg):
        self.latest_cmd = msg
        self.last_cmd_time = time.monotonic()

    def beacon_cb(self, msg):
        new_state = bool(msg.data)
        if new_state and not self.beacon_state:
            self.beep_pending = True
        if not new_state:
            self.beep_pending = False
        self.beacon_state = new_state

    def handle_line(self, line):
        if line == PROTOCOL_READY:
            if not self.ready:
                self.ready = True
                self.last_cmd_time = 0.0
                self.get_logger().info('Arduino firmware protocol READY,1')
            return
        if line.startswith('ENC,') or line.startswith('ACK,') or line.startswith('ERR,'):
            self.telemetry_pub.publish(String(data=line))
            if line.startswith('ERR,'):
                self.get_logger().warning(f'Arduino: {line}')
        elif line in ('SOUND,0', 'SOUND,1'):
            self.sound_pub.publish(Bool(data=line == 'SOUND,1'))
        elif line:
            self.get_logger().warning(f'Unexpected Arduino line: {line}')

    def read_serial(self):
        if self.ser is None:
            return
        try:
            count = min(self.ser.in_waiting, 1024)
            if count:
                self.recv_buffer.extend(self.ser.read(count))
            if len(self.recv_buffer) > 4096:
                self.recv_buffer.clear()
                self.get_logger().warning('Arduino receive buffer overflow')
                return
            while b'\n' in self.recv_buffer:
                raw, _, rest = self.recv_buffer.partition(b'\n')
                self.recv_buffer = bytearray(rest)
                self.handle_line(raw.decode('utf-8', 'replace').strip())
        except Exception as exc:
            self.get_logger().error(f'Serial read failed: {exc}')
            self.disconnect()

    def timer_cb(self):
        if not self.ensure_serial():
            self.ready_pub.publish(Bool(data=False))
            return

        self.read_serial()
        if self.ser is None:
            self.ready_pub.publish(Bool(data=False))
            return

        now = time.monotonic()
        if not self.ready:
            if now - self.last_hello_time >= 0.5:
                self.send_line('HELLO')
                self.last_hello_time = now
            self.ready_pub.publish(Bool(data=False))
            return

        cmd = Twist()
        if (
            self.enable_motion
            and self.last_cmd_time > 0.0
            and now - self.last_cmd_time <= self.cmd_timeout_sec
        ):
            cmd = self.latest_cmd

        if not self.send_line(
            f'CMD,{cmd.linear.x:.3f},{cmd.angular.z:.3f}'
        ):
            self.ready_pub.publish(Bool(data=False))
            return

        if self.beep_pending and self.send_line('BEEP,1'):
            self.beep_pending = False

        self.ready_pub.publish(Bool(data=self.ready))

    def destroy_node(self):
        if self.ready:
            self.send_line('CMD,0.000,0.000')
        self.disconnect()
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
