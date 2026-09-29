import math
import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import Bool, String

try:
    import serial
except ImportError:
    serial = None


# 다른 스케치가 장착된 보드에 주행 명령을 보내지 않기 위한 버전 확인값.
PROTOCOL_READY = 'READY,1'


class SerialBridgeNode(Node):
    """Nano Every USB 연결을 관리하고 호환 펌웨어에만 명령을 보낸다."""

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
        self.declare_parameter('enable_audio', True)
        self.declare_parameter('max_linear_speed', 0.20)
        self.declare_parameter('max_angular_speed', 0.70)
        self.declare_parameter('log_motor_commands', False)
        self.declare_parameter('soft_motion', False)
        self.declare_parameter('linear_accel_limit', 0.10)
        self.declare_parameter('angular_accel_limit', 0.50)
        self.declare_parameter('trial_stop_topic', '/trial_stop')
        self.declare_parameter('trial_motion_window_sec', 0.0)

        p = lambda name: self.get_parameter(name).value
        self.port = str(p('port'))
        self.baud = int(p('baud'))
        self.send_rate_hz = float(p('send_rate_hz'))
        self.reconnect_sec = float(p('reconnect_sec'))
        self.cmd_timeout_sec = float(p('cmd_timeout_sec'))
        self.enable_motion = bool(p('enable_motion'))
        self.enable_audio = bool(p('enable_audio'))
        self.max_linear_speed = float(p('max_linear_speed'))
        self.max_angular_speed = float(p('max_angular_speed'))
        self.log_motor_commands = bool(p('log_motor_commands'))
        self.soft_motion = bool(p('soft_motion'))
        self.linear_accel_limit = float(p('linear_accel_limit'))
        self.angular_accel_limit = float(p('angular_accel_limit'))
        self.trial_motion_window_sec = float(p('trial_motion_window_sec'))
        if not all(
            math.isfinite(value) and value > 0.0
            for value in (
                self.max_linear_speed, self.max_angular_speed,
                self.linear_accel_limit, self.angular_accel_limit,
            )
        ):
            raise ValueError('Motor speed limits must be positive finite numbers')
        if not math.isfinite(self.trial_motion_window_sec) or self.trial_motion_window_sec < 0.0:
            raise ValueError('Trial motion window must be nonnegative and finite')

        self.ser = None
        self.ready = False
        self.recv_buffer = bytearray()
        self.last_reconnect_attempt = 0.0
        self.last_hello_time = 0.0
        self.latest_cmd = Twist()
        self.last_cmd_time = 0.0
        self.beacon_state = False
        self.beep_pending = False
        self.last_command_log_time = 0.0
        self.output_linear = 0.0
        self.output_angular = 0.0
        self.last_output_time = 0.0
        self.trial_stop_latched = False
        self.ready_since = 0.0

        self.create_subscription(
            Twist, p('cmd_topic'), self.cmd_cb, 10
        )
        self.create_subscription(
            Bool, p('beacon_topic'), self.beacon_cb, 10
        )
        self.create_subscription(
            Bool, p('trial_stop_topic'), self.trial_stop_cb, 10
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
            f'enable_motion={self.enable_motion}, '
            f'enable_audio={self.enable_audio}, '
            f'soft_motion={self.soft_motion}, '
            f'limits=({self.max_linear_speed:.3f} m/s, '
            f'{self.max_angular_speed:.3f} rad/s)'
        )

    def disconnect(self):
        # 재연결 후에는 새 /cmd_vel을 받아야 주행할 수 있다.
        if self.ser is not None:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser = None
        self.ready = False
        self.recv_buffer.clear()
        self.last_cmd_time = 0.0
        self.output_linear = 0.0
        self.output_angular = 0.0
        self.last_output_time = 0.0
        self.ready_since = 0.0
        self.beep_pending = self.beacon_state

    def ensure_serial(self):
        # 포트가 없을 때 빠르게 반복 연결하지 않도록 간격을 둔다.
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
            self.output_linear = 0.0
            self.output_angular = 0.0
            self.last_output_time = 0.0
            self.ready_since = 0.0
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

    def trial_stop_cb(self, msg):
        # 한 번 정지 요청을 받으면 이 브리지가 끝날 때까지 재출발하지 않는다.
        if msg.data:
            self.trial_stop_latched = True
            self.get_logger().info('Trial stop latched; ramping to zero')

    @staticmethod
    def approach(current, target, max_step):
        return current + max(-max_step, min(max_step, target - current))

    def limited_cmd(self, msg):
        """Cap both axes together so a slow trial keeps the requested curve."""
        linear = msg.linear.x
        angular = msg.angular.z
        if not math.isfinite(linear) or not math.isfinite(angular):
            return 0.0, 0.0
        scale = min(
            1.0,
            self.max_linear_speed / abs(linear) if linear else 1.0,
            self.max_angular_speed / abs(angular) if angular else 1.0,
        )
        return linear * scale, angular * scale

    def beacon_cb(self, msg):
        # ALERT가 처음 켜질 때 한 번 재생한다. 재연결 시에는 다시 요청한다.
        new_state = bool(msg.data)
        if new_state and not self.beacon_state:
            self.beep_pending = True
        if not new_state:
            self.beep_pending = False
        self.beacon_state = new_state

    def handle_line(self, line):
        # READY,1 전에는 Arduino가 같은 프로토콜인지 확인되지 않았다.
        if line == PROTOCOL_READY:
            if not self.ready:
                self.ready = True
                self.ready_since = time.monotonic()
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
        # 직렬 입력은 줄바꿈 기준이며, 비정상적으로 긴 입력은 버린다.
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
        # 1) 연결 2) 펌웨어 확인 3) 최신 명령 전달 순서로 진행한다.
        if not self.ensure_serial():
            self.ready_pub.publish(Bool(data=False))
            return

        self.read_serial()
        if self.ser is None:
            self.ready_pub.publish(Bool(data=False))
            return

        now = time.monotonic()
        if (
            self.soft_motion
            and self.trial_motion_window_sec > 0.0
            and self.ready_since > 0.0
            and now - self.ready_since >= self.trial_motion_window_sec
            and not self.trial_stop_latched
        ):
            self.trial_stop_latched = True
            self.get_logger().info('Trial time limit reached; ramping to zero')
        if not self.ready:
            if now - self.last_hello_time >= 0.5:
                self.send_line('HELLO')
                self.last_hello_time = now
            self.ready_pub.publish(Bool(data=False))
            return

        cmd = Twist()
        # 통신/명령이 끊기면 감속을 기다리지 않고 즉시 정지한다.
        fresh = (
            self.enable_motion
            and self.last_cmd_time > 0.0
            and now - self.last_cmd_time <= self.cmd_timeout_sec
        )
        if fresh and not self.trial_stop_latched:
            cmd = self.latest_cmd

        target_linear, target_angular = self.limited_cmd(cmd)
        if self.soft_motion and fresh:
            dt = (
                min(now - self.last_output_time, 0.1)
                if self.last_output_time else 1.0 / self.send_rate_hz
            )
            linear = self.approach(
                self.output_linear, target_linear,
                self.linear_accel_limit * max(dt, 0.0),
            )
            angular = self.approach(
                self.output_angular, target_angular,
                self.angular_accel_limit * max(dt, 0.0),
            )
        else:
            linear, angular = target_linear, target_angular
        if not self.send_line(f'CMD,{linear:.3f},{angular:.3f}'):
            self.ready_pub.publish(Bool(data=False))
            return
        self.output_linear = linear
        self.output_angular = angular
        self.last_output_time = now
        if self.log_motor_commands and now - self.last_command_log_time >= 0.5:
            self.get_logger().info(
                f'Sent motor CMD: v={linear:.3f} m/s, '
                f'w={angular:.3f} rad/s'
            )
            self.last_command_log_time = now

        # 실물 DFPlayer Pro에서 첫 번째 파일(bbibip.mp3)의 재생을 확인했다.
        if self.enable_audio and self.beep_pending and self.send_line('BEEP,2'):
            self.beep_pending = False

        self.ready_pub.publish(Bool(data=self.ready))

    def destroy_node(self):
        # 정상 종료 시에도 정지 명령을 보내고 USB 포트를 닫는다.
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
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
