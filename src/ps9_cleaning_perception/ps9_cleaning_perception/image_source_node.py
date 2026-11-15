"""Optional local image/video/USB-camera publisher for demonstrations."""

import math
from pathlib import Path

import cv2
import rclpy
from cv_bridge import CvBridge
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image

from .paths import asset_path


class ImageSourceNode(Node):
    def __init__(self, **kwargs):
        super().__init__('ps9_image_source', **kwargs)
        self.capture = None
        try:
            self._configure()
        except Exception:
            self.destroy_node()
            raise

    def _parameter(self, name, value):
        return self.declare_parameter(name, value, ParameterDescriptor(read_only=True)).value

    def _configure(self):
        source = self._parameter('source', '') or str(asset_path('samples/sample.png'))
        fps = float(self._parameter('fps', 5.0))
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError('fps must be finite and positive')
        self.frame_id = self._parameter('frame_id', 'camera_optical_frame')
        self.loop = self._parameter('loop_video', False)
        topic = self._parameter('image_topic', '/camera/image_raw')
        self.still = None
        self.is_video_file = False
        if source.isdecimal():
            self.capture = cv2.VideoCapture(int(source))
        else:
            path = Path(source).expanduser().resolve()
            if not path.exists():
                raise FileNotFoundError(f'Image, video or camera path not found: {path}')
            if path.suffix.lower() in ('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff', '.webp'):
                self.still = cv2.imread(str(path), cv2.IMREAD_COLOR)
                if self.still is None:
                    raise ValueError(f'Cannot decode image: {path}')
            else:
                self.is_video_file = path.is_file()
                self.capture = cv2.VideoCapture(str(path))
        if self.capture is not None and not self.capture.isOpened():
            raise RuntimeError(f'Cannot open camera/video: {source}')
        self.bridge = CvBridge()
        self.publisher = self.create_publisher(
            Image, topic, QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT),
        )
        self.timer = self.create_timer(1.0 / fps, self._publish_frame)
        self.get_logger().info(f'Publishing {source} to {self.publisher.topic_name} at {fps:g} Hz')

    def _publish_frame(self):
        frame = self.still
        if frame is None:
            ok, frame = self.capture.read()
            if not ok and self.loop and self.is_video_file:
                self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = self.capture.read()
            if not ok:
                self.get_logger().warning('Video ended or camera read failed; stopping publisher')
                self.timer.cancel()
                self.capture.release()
                return
        message = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        # Time is publication/capture-read time, not an original video timestamp.
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = self.frame_id
        self.publisher.publish(message)

    def destroy_node(self):
        if self.capture is not None:
            self.capture.release()
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = ImageSourceNode()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
