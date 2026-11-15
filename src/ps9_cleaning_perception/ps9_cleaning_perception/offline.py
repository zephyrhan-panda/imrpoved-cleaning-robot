"""Run the same detector without ROS for a single-image smoke check."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import time

import cv2

from .core import DetectorConfig, YoloDetector, annotate
from .paths import asset_path


def main(args=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', default=None)
    parser.add_argument('--source', default=None)
    parser.add_argument('--conf', type=float, default=0.30)
    parser.add_argument('--iou', type=float, default=0.70)
    parser.add_argument('--imgsz', type=int, default=640)
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--exclude-classes', default='')
    parser.add_argument('--output', default='demo_output')
    options = parser.parse_args(args)
    model = Path(options.model).expanduser().resolve() if options.model else asset_path('models/best.onnx')
    source = Path(options.source).expanduser().resolve() if options.source else asset_path('samples/sample.png')
    if not source.is_file():
        raise FileNotFoundError(f'Input image not found: {source}')
    frame = cv2.imread(str(source), cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError(f'Cannot decode image: {source}')
    detector = YoloDetector(DetectorConfig(
        str(model), confidence=options.conf, iou=options.iou,
        image_size=options.imgsz, device=options.device,
        exclude_classes=tuple(x.strip() for x in options.exclude_classes.split(',') if x.strip()),
    ))
    start = time.perf_counter()
    prediction = detector.predict(frame)
    elapsed = time.perf_counter() - start
    output = Path(options.output).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output / 'annotated.jpg'), annotate(frame, prediction)):
        raise OSError('Unable to save annotated image')
    data = {
        'model': str(model), 'source': str(source), 'first_inference_seconds': elapsed,
        'width': prediction.width, 'height': prediction.height,
        'class_names': prediction.class_names,
        'detections': [asdict(d) for d in prediction.detections],
    }
    (output / 'detections.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    print(f'{len(prediction.detections)} detections; outputs: {output}')


if __name__ == '__main__':
    main()
