"""ROS-independent inference; preprocessing and NMS remain in Ultralytics."""

from dataclasses import dataclass
import math
import os
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np


@dataclass(frozen=True)
class DetectorConfig:
    model_path: str
    confidence: float = 0.30
    iou: float = 0.70
    image_size: int = 640
    device: str = 'cpu'
    max_detections: int = 300
    exclude_classes: tuple[str, ...] = ()

    def __post_init__(self):
        for name in ('confidence', 'iou'):
            value = getattr(self, name)
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f'{name} must be a finite number in [0, 1]')
        if isinstance(self.image_size, bool) or not isinstance(self.image_size, int):
            raise ValueError('image_size must be an integer')
        if self.image_size < 32 or self.image_size % 32:
            raise ValueError('image_size must be a positive multiple of 32')
        if (isinstance(self.max_detections, bool)
                or not isinstance(self.max_detections, int) or self.max_detections < 1):
            raise ValueError('max_detections must be a positive integer')
        if not isinstance(self.device, str) or not self.device.strip():
            raise ValueError('device must be cpu, mps, or an explicit GPU device string')


@dataclass(frozen=True)
class Detection:
    class_id: int
    class_name: str
    score: float
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def size(self) -> tuple[float, float]:
        return (self.x2 - self.x1, self.y2 - self.y1)


@dataclass(frozen=True)
class Prediction:
    detections: tuple[Detection, ...]
    class_names: dict[int, str]
    width: int
    height: int


def decode_detections(
    xyxy, scores, class_ids, names: Mapping[int, str],
    width: int, height: int, exclude_classes: Sequence[str] = (),
) -> tuple[Detection, ...]:
    """Clip original-image pixel boxes; never infer class IDs from classes.txt."""
    if width <= 0 or height <= 0:
        raise ValueError('Image dimensions must be positive')
    if not (len(xyxy) == len(scores) == len(class_ids)):
        raise ValueError('Detection arrays have inconsistent lengths')
    excluded = set(exclude_classes)
    detections = []
    for box, score, raw_id in zip(xyxy, scores, class_ids):
        values = [*box, score, raw_id]
        if len(box) != 4 or not all(math.isfinite(float(v)) for v in values):
            continue
        class_id = int(raw_id)
        if float(raw_id) != class_id or class_id not in names:
            raise ValueError(f'Unexpected model class ID: {raw_id}')
        name = str(names[class_id])
        if name in excluded or not 0 <= float(score) <= 1:
            continue
        x1, y1, x2, y2 = map(float, box)
        x1, x2 = max(0., min(x1, width)), max(0., min(x2, width))
        y1, y2 = max(0., min(y1, height)), max(0., min(y2, height))
        if x2 <= x1 or y2 <= y1:
            continue
        detections.append(Detection(class_id, name, float(score), x1, y1, x2, y2))
    return tuple(detections)


class YoloDetector:
    def __init__(self, config: DetectorConfig):
        self.config = config
        path = Path(config.model_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f'Model does not exist: {path}')
        if path.suffix.lower() not in ('.onnx', '.pt'):
            raise ValueError('This adapter accepts local .onnx or .pt models')
        # Dependency installation belongs to setup, never the running robot.
        os.environ['YOLO_AUTOINSTALL'] = 'false'
        if path.suffix.lower() == '.onnx':
            import onnx
            import onnxruntime
            # Read only graph metadata, not external model data. Avoid a second
            # ONNX Runtime session and its thread pool just for validation.
            graph = onnx.load(str(path), load_external_data=False)
            dims = graph.graph.input[0].type.tensor_type.shape.dim
            if len(dims) != 4:
                raise ValueError('Expected an NCHW ONNX image input')
            static_shape = tuple(d.dim_value for d in dims)
            if static_shape[0] not in (0, 1) or static_shape[1] not in (0, 3):
                raise ValueError(f'Expected batch=1, channels=3; got {static_shape}')
            if any(d and d != config.image_size for d in static_shape[2:]):
                raise ValueError(f'ONNX requires size {static_shape[2:]}; '
                                 f'image_size is {config.image_size}')
            if config.device != 'cpu':
                raise ValueError('The supplied ONNX setup uses CPU. Use best.pt '
                                 'with device:=0 for a configured CUDA environment.')
            if 'CPUExecutionProvider' not in onnxruntime.get_available_providers():
                raise RuntimeError('ONNX Runtime CPUExecutionProvider is unavailable')
        from ultralytics import YOLO
        self.model = YOLO(str(path), task='detect')

    def predict(self, bgr: np.ndarray) -> Prediction:
        if (not isinstance(bgr, np.ndarray) or bgr.dtype != np.uint8
                or bgr.ndim != 3 or bgr.shape[2] != 3 or bgr.size == 0):
            raise ValueError('Expected a non-empty HWC uint8 BGR image')
        cfg = self.config
        result = self.model.predict(
            source=bgr, conf=cfg.confidence, iou=cfg.iou,
            imgsz=cfg.image_size, device=cfg.device, max_det=cfg.max_detections,
            half=False, rect=True, save=False, verbose=False,
        )[0]
        names = {int(k): str(v) for k, v in result.names.items()}
        height, width = bgr.shape[:2]
        if result.boxes is None:
            raise RuntimeError('Model did not return detection boxes')
        boxes = result.boxes.cpu().numpy()
        detections = decode_detections(
            boxes.xyxy, boxes.conf, boxes.cls, names, width, height, cfg.exclude_classes,
        )
        return Prediction(detections, names, width, height)


def annotate(bgr: np.ndarray, prediction: Prediction) -> np.ndarray:
    import cv2
    canvas = bgr.copy()
    palette = ((55, 200, 80), (0, 185, 255), (255, 160, 40), (170, 170, 170))
    for d in prediction.detections:
        color = palette[d.class_id % len(palette)]
        start = (int(d.x1), int(d.y1))
        end = (min(int(d.x2), prediction.width - 1),
               min(int(d.y2), prediction.height - 1))
        cv2.rectangle(canvas, start, end, color, 2)
        cv2.putText(canvas, f'{d.class_name} {d.score:.2f}',
                    (start[0], max(16, start[1] - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)
    return canvas
