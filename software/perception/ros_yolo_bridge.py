"""기존 RDK YOLO 노드를 실행하고 사람 상자를 ROS 미션 노드에 전달한다.

rdk_model_zoo의 YOLO 실행 디렉터리에서 실행하며 해당 디렉터리를 PYTHONPATH에
넣어야 한다. 원본 ros_yolo_live.py와 모델은 저장소 밖에 있다.
"""

import math

import rclpy
from ai_msgs.msg import PerceptionTargets, Roi, Target
from ros_yolo_live import CLASS_NAMES, RescueYoloNode


DETECTION_TOPIC = '/rescue_yolo_detections'


def build_perception_message(boxes, scores, class_ids, width, height, stamp):
    """원본 영상 좌표의 YOLO 상자를 ai_msgs 사람 탐지 메시지로 바꾼다."""
    result = PerceptionTargets()
    result.header.stamp = stamp
    result.header.frame_id = 'camera_left'

    for box, score, class_id in zip(boxes, scores, class_ids):
        # 점수·클래스·좌표가 깨진 결과는 ROS로 전달하지 않는다.
        if not math.isfinite(float(score)):
            continue

        class_id = int(class_id)
        if not 0 <= class_id < len(CLASS_NAMES):
            continue

        if not all(math.isfinite(float(value)) for value in box):
            continue

        x1, y1, x2, y2 = [float(value) for value in box]
        # 영상 밖으로 벗어난 상자는 영상 경계 안으로 잘라낸다.
        x1 = max(0, min(width, round(x1)))
        y1 = max(0, min(height, round(y1)))
        x2 = max(0, min(width, round(x2)))
        y2 = max(0, min(height, round(y2)))
        if x2 <= x1 or y2 <= y1:
            continue

        target = Target()
        # fallen/sit/standing을 모두 미션에서 이해하는 person으로 통일한다.
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
        # 빈 탐지 프레임도 발행해 추적 노드가 대상 상실을 즉시 알게 한다.
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
