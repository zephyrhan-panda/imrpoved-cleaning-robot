"""Only this adapter depends on ROS message classes."""

from copy import deepcopy
from vision_msgs.msg import Detection2D, Detection2DArray, ObjectHypothesisWithPose


def to_detection_array(prediction, header):
    message = Detection2DArray()
    message.header = deepcopy(header)
    for item in prediction.detections:
        detection = Detection2D()
        detection.header = deepcopy(header)
        detection.bbox.center.position.x = float(item.center[0])
        detection.bbox.center.position.y = float(item.center[1])
        detection.bbox.center.theta = 0.0
        detection.bbox.size_x = float(item.size[0])
        detection.bbox.size_y = float(item.size[1])
        hypothesis = ObjectHypothesisWithPose()
        hypothesis.hypothesis.class_id = str(item.class_id)
        hypothesis.hypothesis.score = float(item.score)
        detection.results.append(hypothesis)
        # No tracker or metric pose is estimated: leave id and pose unset.
        message.detections.append(detection)
    return message
