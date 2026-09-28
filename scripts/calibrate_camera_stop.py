#!/usr/bin/env python3
"""Measure fallen detection boxes at a known distance without motor commands."""

import argparse
from collections import Counter
from statistics import median
import time

import rclpy
from ai_msgs.msg import PerceptionTargets
from rclpy.node import Node


class DetectionSampler(Node):
    def __init__(self):
        super().__init__('fallen_distance_sampler')
        self.frames = 0
        self.labels = Counter()
        self.widths = []
        self.heights = []
        self.scores = []
        self.create_subscription(
            PerceptionTargets, '/rescue_yolo_detections', self.on_frame, 10
        )

    def on_frame(self, message):
        self.frames += 1
        for target in message.targets:
            self.labels[str(target.type).lower()] += 1

        # 주행 노드와 똑같이 면적이 가장 큰 fallen 상자를 사용한다.
        boxes = []
        for target in message.targets:
            if str(target.type).lower() != 'fallen':
                continue
            for roi in target.rois:
                boxes.append(roi)
        if not boxes:
            return
        roi = max(boxes, key=lambda item: item.rect.width * item.rect.height)
        self.widths.append(float(roi.rect.width) / 1920.0)
        self.heights.append(float(roi.rect.height) / 1080.0)
        self.scores.append(float(roi.confidence))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=8.0)
    args = parser.parse_args()
    if not 0 < args.seconds <= 30:
        parser.error('--seconds는 0초 초과 30초 이하여야 합니다')

    rclpy.init()
    node = DetectionSampler()
    print('영상 탐지만 측정합니다. 모터 명령은 보내지 않습니다.', flush=True)
    try:
        deadline = time.monotonic() + args.seconds
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.2)
        detected = len(node.widths)
        print(f'영상 {node.frames}프레임, fallen 탐지 {detected}프레임')
        print(f'탐지 클래스: {dict(node.labels)}')
        if detected:
            print(
                f'fallen 상자 중앙값: 폭 {median(node.widths):.2f}, '
                f'높이 {median(node.heights):.2f}, '
                f'신뢰도 {median(node.scores):.2f}'
            )
            print(
                f'fallen 상자 범위: 폭 {min(node.widths):.2f}~'
                f'{max(node.widths):.2f}, 높이 {min(node.heights):.2f}~'
                f'{max(node.heights):.2f}'
            )
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
