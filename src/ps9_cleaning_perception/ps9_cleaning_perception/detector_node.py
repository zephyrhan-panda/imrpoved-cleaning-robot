"""Subscribe to ROS images and publish timestamp-aligned 2D detections."""

import json
import math
from pathlib import Path
import time

import numpy as np
import rclpy
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor, ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from rcl_interfaces.msg import ParameterDescriptor
from cv_bridge import CvBridge
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from sensor_msgs.msg import Image
from std_msgs.msg import String
from vision_msgs.msg import Detection2DArray

from .buffering import LatestFrame, is_stale
from .core import DetectorConfig, YoloDetector, annotate
from .messages import to_detection_array
from .paths import asset_path


class DetectorNode(Node):
    def __init__(self, *, detector_factory=YoloDetector, **kwargs):
        super().__init__('ps9_detector', **kwargs)
        try:
            self._configure(detector_factory)
        except Exception:
            self.destroy_node()
            raise

    def _parameter(self, name, value):
        return self.declare_parameter(
            name, value, ParameterDescriptor(read_only=True),
        ).value

    def _configure(self, detector_factory):
        model_path = self._parameter('model_path', '') or str(asset_path('models/best.onnx'))
        image_topic = self._parameter('image_topic', '/camera/image_raw')
        reliability = self._parameter('image_reliability', 'best_effort')
        if reliability not in ('best_effort', 'reliable'):
            raise ValueError('image_reliability must be best_effort or reliable')
        config = DetectorConfig(
            model_path=model_path,
            confidence=self._parameter('confidence', 0.30),
            iou=self._parameter('iou', 0.70),
            image_size=self._parameter('image_size', 640),
            device=self._parameter('device', 'cpu'),
            max_detections=self._parameter('max_detections', 300),
            exclude_classes=tuple(x.strip() for x in
                                  self._parameter('exclude_classes', '').split(',') if x.strip()),
        )
        self.max_age = float(self._parameter('max_image_age_sec', 2.0))
        max_fps = float(self._parameter('max_fps', 10.0))
        self.publish_annotated = self._parameter('publish_annotated', True)
        for key, value in [('max_image_age_sec', self.max_age), ('max_fps', max_fps)]:
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f'{key} must be finite and positive')
        self.bridge = CvBridge()
        self.frames = LatestFrame()
        self.processed = self.failed = self.stale = 0
        self.last_success = None
        self.last_error = ''
        self.latency_ms = 0.0
        self.get_logger().info(f'Loading {model_path} on {config.device}')
        self.detector = detector_factory(config)
        warmup = self.detector.predict(np.zeros((config.image_size, config.image_size, 3), np.uint8))

        sensor_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST, depth=1,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )
        input_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST, depth=1,
            reliability=(ReliabilityPolicy.BEST_EFFORT if reliability == 'best_effort'
                         else ReliabilityPolicy.RELIABLE),
            durability=DurabilityPolicy.VOLATILE,
        )
        metadata_qos = QoSProfile(
            depth=1, reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self.detections_pub = self.create_publisher(Detection2DArray, 'detections', 1)
        self.annotated_pub = (self.create_publisher(Image, 'annotated_image', sensor_qos)
                              if self.publish_annotated else None)
        self.classes_pub = self.create_publisher(String, 'class_map', metadata_qos)
        self.diagnostics_pub = self.create_publisher(DiagnosticArray, 'diagnostics', 1)
        self.classes_pub.publish(String(data=json.dumps({
            'model': Path(model_path).name,
            'classes': warmup.class_names,
            'excluded_classes': list(config.exclude_classes),
            'coordinates': 'original image pixels',
        }, ensure_ascii=False)))
        # Independent callback groups let new input replace the pending frame
        # while inference runs. Inference itself is never concurrent.
        self.input_group = MutuallyExclusiveCallbackGroup()
        self.inference_group = MutuallyExclusiveCallbackGroup()
        self.subscription = self.create_subscription(
            Image, image_topic, self.frames.put, input_qos,
            callback_group=self.input_group,
        )
        self.inference_timer = self.create_timer(
            1.0 / max_fps, self._process, callback_group=self.inference_group,
        )
        self.health_timer = self.create_timer(1.0, self._publish_diagnostics)
        self.get_logger().info(
            f'Ready: {image_topic} -> {self.detections_pub.topic_name}; '
            f'classes={warmup.class_names}'
        )

    def _expired(self, message, received_at):
        stamp = message.header.stamp
        return is_stale(stamp.sec * 1_000_000_000 + stamp.nanosec,
                        self.get_clock().now().nanoseconds,
                        received_at, time.monotonic(), self.max_age)

    def _process(self):
        pending = self.frames.take()
        if pending is None:
            return
        message, received_at = pending
        if self._expired(message, received_at):
            self.stale += 1
            return
        started = time.monotonic()
        try:
            frame = self.bridge.imgmsg_to_cv2(message, desired_encoding='bgr8')
            prediction = self.detector.predict(frame)
            # Check again: a slow inference must not publish an obsolete result.
            if self._expired(message, received_at):
                self.stale += 1
                return
            detections = to_detection_array(prediction, message.header)
            annotated = None
            if self.annotated_pub is not None:
                annotated = self.bridge.cv2_to_imgmsg(annotate(frame, prediction), encoding='bgr8')
                annotated.header = message.header
            if self._expired(message, received_at):
                self.stale += 1
                return
            self.detections_pub.publish(detections)
            if annotated is not None:
                self.annotated_pub.publish(annotated)
            self.processed += 1
            self.last_success = time.monotonic()
            self.latency_ms = (self.last_success - started) * 1000.0
            self.last_error = ''
        except Exception as exc:
            self.failed += 1
            self.last_error = f'{type(exc).__name__}: {exc}'
            self.get_logger().error(self.last_error, throttle_duration_sec=5.0)
            # Errors are reported through diagnostics, never as "no dirt".

    def _publish_diagnostics(self):
        status = DiagnosticStatus()
        status.name = self.get_fully_qualified_name()
        status.hardware_id = 'ps9_cleaning_perception'
        if self.last_error:
            status.level, status.message = DiagnosticStatus.ERROR, self.last_error
        elif self.last_success is None:
            status.level, status.message = DiagnosticStatus.WARN, 'Waiting for a usable image'
        elif time.monotonic() - self.last_success > self.max_age:
            status.level, status.message = DiagnosticStatus.STALE, 'No recent successful inference'
        else:
            status.level, status.message = DiagnosticStatus.OK, 'Inference active'
        status.values = [KeyValue(key=key, value=str(value)) for key, value in {
            'processed': self.processed, 'failed': self.failed,
            'stale_dropped': self.stale, 'replaced_pending': self.frames.replaced,
            'last_latency_ms': round(self.latency_ms, 2),
        }.items()]
        array = DiagnosticArray()
        array.header.stamp = self.get_clock().now().to_msg()
        array.status.append(status)
        self.diagnostics_pub.publish(array)


def main(args=None):
    rclpy.init(args=args)
    node = executor = None
    try:
        node = DetectorNode()
        executor = MultiThreadedExecutor(num_threads=2)
        executor.add_node(node)
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if executor is not None:
            executor.shutdown()
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
