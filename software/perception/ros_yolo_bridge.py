"""Run the existing RDK YOLO node and publish its boxes for rescue_beacon.

Run this from the rdk_model_zoo YOLO runtime directory with that directory on
PYTHONPATH. The original ros_yolo_live.py and its model remain unchanged.
"""

import math

import rclpy
from ai_msgs.msg import PerceptionTargets, Roi, Target
from ros_yolo_live import CLASS_NAMES, RescueYoloNode


DETECTION_TOPIC = '/rescue_yolo_detections'


def build_perception_message(boxes, scores, class_ids, width, height, stamp):
    """Convert YOLO boxes in source-image pixels into ai_msgs targets."""
    result = PerceptionTargets()
    result.header.stamp = stamp
    result.header.frame_id = 'camera_left'

    for box, score, class_id in zip(boxes, scores, class_ids):
        if not math.isfinite(float(score)):
            continue

        class_id = int(class_id)
        if not 0 <= class_id < len(CLASS_NAMES):
            continue

        if not all(math.isfinite(float(value)) for value in box):
            continue

        x1, y1, x2, y2 = [float(value) for value in box]
        x1 = max(0, min(width, round(x1)))
        y1 = max(0, min(height, round(y1)))
        x2 = max(0, min(width, round(x2)))
        y2 = max(0, min(height, round(y2)))
        if x2 <= x1 or y2 <= y1:
            continue

        target = Target()
        target.type = 'person'

        roi = Roi()
        roi.type = 'body'
        roi.confidence = float(score)
        roi.rect.x_offset = x1
        roi.rect.y_offset = y1
        roi.rect.width = x2 - x1
        roi.rect.height = y2 - y1
        target.rois.append(roi)
        result.targets.append(target)

    return result


class RescueYoloBridge(RescueYoloNode):
    def __init__(self):
        super().__init__()
        self.detection_pub = self.create_publisher(
            PerceptionTargets, DETECTION_TOPIC, 10
        )
        self.get_logger().info(f'Detection output: {DETECTION_TOPIC}')

    def draw_detections(self, frame, boxes, scores, class_ids):
        height, width = frame.shape[:2]
        result = build_perception_message(
            boxes,
            scores,
            class_ids,
            width,
            height,
            self.get_clock().now().to_msg(),
        )
        self.detection_pub.publish(result)
        super().draw_detections(frame, boxes, scores, class_ids)


def main(args=None):
    rclpy.init(args=args)
    node = RescueYoloBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
