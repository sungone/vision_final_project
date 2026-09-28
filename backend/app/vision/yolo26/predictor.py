from __future__ import annotations

import logging
import time
from pathlib import Path

import numpy as np
import torch
from ultralytics import YOLO


logger = logging.getLogger(__name__)


class YOLO26SegPredictor:
    def __init__(
        self,
        model_path: str,
        device_name: str = "auto",
        image_size: int = 640,
        score_threshold: float = 0.7,
        iou_threshold: float = 0.7,
        max_detections: int = 100,
        use_half: bool = True,
    ) -> None:
        self.model_path = Path(model_path)
        if not self.model_path.is_file():
            raise FileNotFoundError(f"YOLO26 model not found: {self.model_path}")
        self.device, self.device_name = self._resolve_device(device_name)
        self.image_size = image_size
        self.score_threshold = score_threshold
        self.iou_threshold = iou_threshold
        self.max_detections = max_detections
        self.use_half = use_half and self.device_name.startswith("cuda")
        self.model = YOLO(str(self.model_path))
        if self.model.task != "segment":
            raise ValueError(f"YOLO model must be a segmentation model, got task={self.model.task!r}")
        self.label_to_name = {int(key): str(value) for key, value in self.model.names.items()}
        logger.info(
            "YOLO26 segmentation model loaded from %s on %s with classes=%s",
            self.model_path,
            self.device_name,
            self.label_to_name,
        )

    def predict(self, frame: np.ndarray):
        if frame is None or frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError("YOLO26 input must be a BGR image with three channels")
        started = time.perf_counter()
        result = self.model.predict(
            source=frame,
            imgsz=self.image_size,
            conf=self.score_threshold,
            iou=self.iou_threshold,
            max_det=self.max_detections,
            device=self.device,
            quantize=16 if self.use_half else None,
            retina_masks=True,
            verbose=False,
        )[0]
        if self.device_name.startswith("cuda"):
            torch.cuda.synchronize()
        return result, (time.perf_counter() - started) * 1000.0

    @staticmethod
    def _resolve_device(device_name: str) -> tuple[str | int, str]:
        requested = device_name.strip().lower()
        if requested == "auto":
            return (0, "cuda:0") if torch.cuda.is_available() else ("cpu", "cpu")
        if requested.startswith("cuda"):
            if not torch.cuda.is_available():
                logger.warning("CUDA was requested but is unavailable; falling back to CPU")
                return "cpu", "cpu"
            index = requested.split(":", 1)[1] if ":" in requested else "0"
            return int(index), f"cuda:{index}"
        if requested == "cpu":
            return "cpu", "cpu"
        raise ValueError(f"invalid VISION_DEVICE: {device_name}")
