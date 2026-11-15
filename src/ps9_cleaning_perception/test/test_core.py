import math
import pytest
from ps9_cleaning_perception.core import DetectorConfig, decode_detections
from ps9_cleaning_perception.buffering import LatestFrame, is_stale


NAMES = {0: 'bigdirt', 1: 'dirt', 2: 'water', 3: 'background'}


def test_pixel_geometry_and_model_class_order():
    result = decode_detections([[-5, 10, 120, 90]], [0.8], [0], NAMES, 100, 80)
    assert len(result) == 1
    detection = result[0]
    assert detection.class_name == 'bigdirt'
    assert detection.center == (50.0, 45.0)
    assert detection.size == (100.0, 70.0)


def test_background_is_preserved_unless_explicitly_excluded():
    args = ([[0, 0, 10, 20]], [0.9], [3], NAMES, 100, 80)
    assert decode_detections(*args)[0].class_name == 'background'
    assert decode_detections(*args, exclude_classes=['background']) == ()


def test_empty_and_invalid_boxes():
    assert decode_detections([], [], [], NAMES, 100, 80) == ()
    assert decode_detections([[20, 0, 10, 20], [0, 0, math.nan, 20]],
                             [0.8, 0.8], [0, 0], NAMES, 100, 80) == ()
    with pytest.raises(ValueError, match='class ID'):
        decode_detections([[0, 0, 10, 20]], [0.9], [8], NAMES, 100, 80)


@pytest.mark.parametrize('kwargs', [
    {'confidence': -0.1}, {'confidence': float('nan')}, {'iou': 1.1},
    {'image_size': 0}, {'image_size': 641}, {'image_size': 640.5},
    {'max_detections': 0}, {'device': ''},
])
def test_invalid_configuration_rejected(kwargs):
    with pytest.raises(ValueError):
        DetectorConfig('model.onnx', **kwargs)


def test_pending_frames_are_replaced_not_queued_or_reprocessed():
    slot = LatestFrame()
    slot.put('old', received_at=1.0)
    slot.put('latest', received_at=2.0)
    assert slot.replaced == 1
    assert slot.take() == ('latest', 2.0)
    assert slot.take() is None


def test_freshness_checks_capture_and_arrival_time():
    assert not is_stale(0, 10_000_000_000, 10., 10.1, 2.)
    assert is_stale(1_000_000_000, 10_000_000_000, 10., 10.1, 2.)
    assert is_stale(0, 10_000_000_000, 1., 10., 2.)
    assert not is_stale(9_000_000_000, 10_000_000_000, 10., 10.1, 2.)
