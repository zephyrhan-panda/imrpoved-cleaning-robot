import os
os.environ['YOLO_AUTOINSTALL'] = 'false'

import cv2
import numpy as np
import pytest
from ultralytics import YOLO

from ps9_cleaning_perception.core import DetectorConfig, YoloDetector
from ps9_cleaning_perception.paths import asset_path


pytestmark = pytest.mark.model


def test_original_onnx_predictions_are_preserved():
    model = asset_path('models/best.onnx')
    source = asset_path('samples/sample.png')
    image = cv2.imread(str(source))
    adapter = YoloDetector(DetectorConfig(str(model)))
    converted = adapter.predict(image)
    # Same invocation as legacy/predict.py, with disk output disabled.
    original = YOLO(str(model), task='detect')(
        str(source), conf=0.30, save=False, verbose=False, device='cpu',
    )[0]
    assert converted.class_names == {0: 'bigdirt', 1: 'dirt', 2: 'water', 3: 'background'}
    assert len(converted.detections) == len(original.boxes)
    assert len(converted.detections) > 0, 'The included smoke sample should exercise real detections'
    np.testing.assert_allclose(
        [[d.x1, d.y1, d.x2, d.y2] for d in converted.detections],
        original.boxes.xyxy.cpu().numpy(), rtol=1e-5, atol=1e-3,
    )
    np.testing.assert_allclose([d.score for d in converted.detections],
                               original.boxes.conf.cpu().numpy(), atol=1e-6)
    assert [d.class_id for d in converted.detections] == original.boxes.cls.int().tolist()


def test_pytorch_alternative_and_input_validation():
    detector = YoloDetector(DetectorConfig(str(asset_path('models/best.pt'))))
    image = cv2.imread(str(asset_path('samples/sample.png')))
    result = detector.predict(image)
    assert result.class_names[0] == 'bigdirt'
    assert result.width == image.shape[1]
    for d in result.detections:
        assert 0 <= d.x1 < d.x2 <= result.width
        assert 0 <= d.y1 < d.y2 <= result.height
    with pytest.raises(ValueError, match='BGR'):
        detector.predict(np.zeros((20, 30), dtype=np.uint8))


def test_missing_model_fails_without_downloading(tmp_path):
    with pytest.raises(FileNotFoundError):
        YoloDetector(DetectorConfig(str(tmp_path / 'yolov8n.pt')))


def test_static_onnx_size_mismatch_is_rejected():
    with pytest.raises(ValueError, match='ONNX requires size'):
        YoloDetector(DetectorConfig(str(asset_path('models/best.onnx')), image_size=320))
