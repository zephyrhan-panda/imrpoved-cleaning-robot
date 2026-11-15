"""Real rclpy/DDS tests, explicitly skipped when ROS 2 is not installed."""

import time
import numpy as np
import pytest

rclpy = pytest.importorskip('rclpy', reason='ROS 2 runtime is required for DDS integration')
from rclpy.context import Context
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile, ReliabilityPolicy
from cv_bridge import CvBridge
from sensor_msgs.msg import Image
from std_msgs.msg import Header
from vision_msgs.msg import Detection2DArray

from ps9_cleaning_perception.core import Detection, Prediction
from ps9_cleaning_perception.detector_node import DetectorNode
from ps9_cleaning_perception.messages import to_detection_array
from ps9_cleaning_perception.image_source_node import ImageSourceNode
from ps9_cleaning_perception.paths import asset_path

pytestmark = pytest.mark.integration


class FixedDetector:
    def __init__(self, _config):
        self.empty = False

    def predict(self, image):
        ds = () if self.empty else (Detection(0, 'bigdirt', 0.8, 5., 6., 25., 26.),)
        return Prediction(ds, {0: 'bigdirt'}, image.shape[1], image.shape[0])


@pytest.fixture
def ros_scope():
    context = Context()
    rclpy.init(context=context)
    executor = SingleThreadedExecutor(context=context)
    nodes = []

    def register(node):
        nodes.append(node)
        executor.add_node(node)
        return node

    yield context, executor, register
    executor.shutdown()
    for node in reversed(nodes):
        node.destroy_node()
    context.shutdown()


def spin_until(executor, predicate, timeout=10):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        executor.spin_once(timeout_sec=0.05)
    assert predicate(), 'Timed out waiting for ROS messages'


def test_real_vision_message_schema_and_header():
    header = Header()
    header.stamp.sec = 123
    header.stamp.nanosec = 456
    header.frame_id = 'test_camera'
    prediction = FixedDetector(None).predict(np.zeros((40, 50, 3), dtype=np.uint8))
    msg = to_detection_array(prediction, header)
    d = msg.detections[0]
    assert msg.header == d.header == header
    assert d.bbox.center.position.x == 15.0
    assert d.bbox.center.position.y == 16.0
    assert d.bbox.size_x == d.bbox.size_y == 20.0
    assert d.results[0].hypothesis.class_id == '0'
    assert d.results[0].hypothesis.score == 0.8
    assert d.id == ''
    assert to_detection_array(Prediction((), {}, 50, 40), header).detections == []


def test_dds_roundtrip_empty_result_and_bad_encoding(ros_scope):
    context, executor, register = ros_scope
    detector = register(DetectorNode(
        context=context, detector_factory=FixedDetector, namespace='/integration',
        parameter_overrides=[Parameter('image_topic', value='/integration/input'),
                             Parameter('max_image_age_sec', value=30.0)],
    ))
    observer = register(Node('observer', context=context))
    received, overlays = [], []
    observer.create_subscription(Detection2DArray, '/integration/detections', received.append, 10)
    observer.create_subscription(Image, '/integration/annotated_image', overlays.append,
                                 QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT))
    publisher = observer.create_publisher(
        Image, '/integration/input', QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT),
    )
    spin_until(executor, lambda: publisher.get_subscription_count() > 0
               and detector.detections_pub.get_subscription_count() > 0
               and detector.annotated_pub.get_subscription_count() > 0)
    message = CvBridge().cv2_to_imgmsg(np.zeros((40, 50, 3), np.uint8), encoding='bgr8')
    message.header.stamp = observer.get_clock().now().to_msg()
    message.header.frame_id = 'integration_camera'
    publisher.publish(message)
    spin_until(executor, lambda: len(received) == 1 and len(overlays) == 1)
    assert received[0].header == overlays[0].header == message.header
    assert received[0].detections[0].bbox.center.position.x == 15.0

    detector.detector.empty = True
    message.header.stamp = observer.get_clock().now().to_msg()
    publisher.publish(message)
    spin_until(executor, lambda: len(received) == 2)
    assert received[-1].detections == []
    message.encoding = 'not_an_encoding'
    publisher.publish(message)
    spin_until(executor, lambda: detector.failed == 1)
    assert len(received) == 2  # inference failure is not an empty detection


@pytest.mark.model
def test_sample_publisher_to_real_model(ros_scope):
    context, executor, register = ros_scope
    detector = register(DetectorNode(
        context=context, namespace='/real_model',
        parameter_overrides=[Parameter('image_topic', value='/real_model/input'),
                             Parameter('max_image_age_sec', value=30.0)],
    ))
    observer = register(Node('model_observer', context=context))
    received = []
    observer.create_subscription(Detection2DArray, '/real_model/detections', received.append, 10)
    register(ImageSourceNode(
        context=context,
        parameter_overrides=[Parameter('source', value=str(asset_path('samples/sample.png'))),
                             Parameter('image_topic', value='/real_model/input')],
    ))
    spin_until(executor, lambda: bool(received), timeout=30)
    assert received[0].header.frame_id == 'camera_optical_frame'
    assert len(received[0].detections) > 0
    assert detector.failed == 0
