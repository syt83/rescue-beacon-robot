#!/usr/bin/env python3
"""Show the YOLO annotated ROS image and mission status in a local web browser.

This process only subscribes to ROS topics. It never publishes motor commands.
The YOLO runtime already draws boxes and publishes JPEG images, so this server
passes those bytes directly to browsers without running inference again.
"""

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage
from std_msgs.msg import Bool, String


IMAGE_TOPIC = '/yolo/image_annotated/compressed'

PAGE = '''<!doctype html>
<html lang="ko">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Rescue Beacon YOLO Monitor</title>
<style>
  body { margin: 0; background: #111827; color: #f9fafb;
         font: 16px system-ui, sans-serif; }
  main { max-width: 1100px; margin: auto; padding: 20px; }
  h1 { font-size: 22px; margin: 0 0 16px; }
  .status { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 16px; }
  .status span { background: #1f2937; border-radius: 8px; padding: 9px 12px; }
  img { display: block; width: 100%; aspect-ratio: 16 / 9;
        object-fit: contain; background: #030712; border-radius: 10px; }
  p { color: #d1d5db; }
</style>
<main>
  <h1>구조 로봇 YOLO 화면</h1>
  <div class="status">
    <span id="video">영상 대기 중</span>
    <span id="mission">미션: 대기 중</span>
    <span id="arduino">Arduino: 대기 중</span>
  </div>
  <img src="/stream.mjpg" alt="YOLO가 탐지 상자를 표시한 카메라 영상">
  <p>영상이 보이지 않으면 카메라와 YOLO 터미널이 실행 중인지 확인하세요.</p>
</main>
<script>
async function updateStatus() {
  try {
    const response = await fetch('/status', {cache: 'no-store'});
    const status = await response.json();
    document.getElementById('video').textContent = status.frame_age_sec === null
      ? '영상 대기 중' : status.frame_age_sec < 2
        ? 'YOLO 영상 수신 중' : 'YOLO 영상 지연: ' + status.frame_age_sec + '초';
    document.getElementById('mission').textContent =
      '미션: ' + (status.mission_state || '대기 중');
    document.getElementById('arduino').textContent = status.arduino_ready === null
      ? 'Arduino: 연결 정보 없음'
      : 'Arduino: ' + (status.arduino_ready ? '연결됨' : '미연결');
  } catch (_) {
    document.getElementById('video').textContent = '모니터 서버 연결 끊김';
  }
}
updateStatus();
setInterval(updateStatus, 1000);
</script>
</html>
'''.encode('utf-8')


class MonitorState:
    """Share the most recent JPEG and status between ROS and HTTP threads."""

    def __init__(self):
        self.condition = threading.Condition()
        self.frame = None
        self.frame_number = 0
        self.frame_time = None
        self.mission_state = None
        self.mission_time = None
        self.arduino_ready = None
        self.arduino_time = None

    def set_frame(self, data):
        with self.condition:
            self.frame = bytes(data)
            self.frame_number += 1
            self.frame_time = time.monotonic()
            self.condition.notify_all()

    def next_frame(self, previous_number, timeout=2.0):
        with self.condition:
            self.condition.wait_for(
                lambda: self.frame_number != previous_number,
                timeout=timeout,
            )
            if self.frame_number == previous_number:
                return None
            return self.frame_number, self.frame

    def status(self):
        with self.condition:
            now = time.monotonic()
            age = None if self.frame_time is None else now - self.frame_time
            return {
                'frame_age_sec': None if age is None else round(age, 1),
                'mission_state': self.mission_state
                if self.mission_time is not None and now - self.mission_time < 2
                else None,
                'arduino_ready': self.arduino_ready
                if self.arduino_time is not None and now - self.arduino_time < 2
                else None,
            }


class MonitorNode(Node):
    def __init__(self, state):
        super().__init__('rescue_yolo_monitor')
        self.state = state
        # The existing YOLO publisher uses the default reliable ROS QoS.
        self.create_subscription(CompressedImage, IMAGE_TOPIC, self.on_image, 1)
        self.create_subscription(String, '/mission_state', self.on_mission, 1)
        self.create_subscription(Bool, '/arduino_ready', self.on_arduino, 1)

    def on_image(self, message):
        self.state.set_frame(message.data)

    def on_mission(self, message):
        with self.state.condition:
            self.state.mission_state = message.data
            self.state.mission_time = time.monotonic()

    def on_arduino(self, message):
        with self.state.condition:
            self.state.arduino_ready = bool(message.data)
            self.state.arduino_time = time.monotonic()


class MonitorHandler(BaseHTTPRequestHandler):
    state = None

    def do_GET(self):
        path = self.path.split('?', 1)[0]
        if path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(PAGE)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(PAGE)
        elif path == '/status':
            body = json.dumps(self.state.status()).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)
        elif path == '/stream.mjpg':
            self.send_response(200)
            self.send_header(
                'Content-Type',
                'multipart/x-mixed-replace; boundary=frame',
            )
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            # 0 means no image has arrived yet; wait for the first real frame.
            previous_number = 0
            try:
                while True:
                    item = self.state.next_frame(previous_number)
                    if item is None:
                        continue
                    previous_number, frame = item
                    self.wfile.write(b'--frame\r\n')
                    self.wfile.write(b'Content-Type: image/jpeg\r\n')
                    self.wfile.write(
                        f'Content-Length: {len(frame)}\r\n\r\n'.encode('ascii')
                    )
                    self.wfile.write(frame + b'\r\n')
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                return  # Closing a browser tab ends this client's stream.
        else:
            self.send_error(404)

    def log_message(self, format_string, *args):
        # Browser polling would otherwise fill the launch terminal.
        if self.path != '/status':
            super().log_message(format_string, *args)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8088)
    args = parser.parse_args()

    state = MonitorState()
    MonitorHandler.state = state
    server = ThreadingHTTPServer((args.host, args.port), MonitorHandler)
    server.daemon_threads = True

    rclpy.init()
    node = MonitorNode(state)
    http_thread = threading.Thread(target=server.serve_forever, daemon=True)
    http_thread.start()
    if args.host == '0.0.0.0':
        print(f'YOLO monitor: http://<RDK_IP>:{args.port}', flush=True)
    else:
        print(f'YOLO monitor: http://{args.host}:{args.port}', flush=True)
    print(f'Waiting for {IMAGE_TOPIC}', flush=True)
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        server.shutdown()
        server.server_close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
