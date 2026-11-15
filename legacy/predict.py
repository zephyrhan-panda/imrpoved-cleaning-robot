from __future__ import annotations

import argparse
from pathlib import Path

from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = BASE_DIR / "weights" / "best.onnx"
DEFAULT_SOURCE = BASE_DIR / "data" / "images" / "val" / "sample.png"
DEFAULT_PROJECT = BASE_DIR / "runs"
DEFAULT_NAME = "onnx_infer"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ONNX inference with the trained Ultralytics detector.")
    parser.add_argument("--model", default=str(DEFAULT_MODEL), help="Path to the ONNX model file.")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE), help="Path to the input image.")
    parser.add_argument("--conf", type=float, default=0.3, help="Confidence threshold.")
    parser.add_argument("--project", default=str(DEFAULT_PROJECT), help="Directory for saved prediction outputs.")
    parser.add_argument("--name", default=DEFAULT_NAME, help="Subdirectory name for prediction outputs.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model_path = Path(args.model).expanduser().resolve()
    source_path = Path(args.source).expanduser().resolve()
    project_path = Path(args.project).expanduser().resolve()

    if not model_path.is_file():
        raise FileNotFoundError(f"ONNX model not found: {model_path}")
    if not source_path.is_file():
        raise FileNotFoundError(f"Input image not found: {source_path}")

    model = YOLO(model_path, task="detect")
    results = model(
        str(source_path),
        save=True,
        conf=args.conf,
        project=str(project_path),
        name=args.name,
        exist_ok=True,
        verbose=False,
    )

    output_dir = Path(results[0].save_dir)
    print(f"Model: {model_path}")
    print(f"Input: {source_path}")
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    main()
