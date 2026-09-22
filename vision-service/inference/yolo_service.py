from __future__ import annotations

import hashlib
import math
import threading
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from inference.errors import ModelNotAvailableError, VisionInferenceError
from inference.schemas import BoundingBox, Detection, SegmentationResponse


ModelLoader = Callable[[str], Any]


class YoloSegmentationService:
    """Lazy, serialized adapter around an Ultralytics segmentation model."""

    def __init__(
        self,
        model_path: Path,
        *,
        model_loader: ModelLoader | None = None,
        max_detections: int = 1_000,
        max_polygon_points: int = 10_000,
        max_total_polygon_points: int = 200_000,
    ) -> None:
        self._model_path = model_path
        self._model_loader = model_loader or self._load_ultralytics_model
        self._max_detections = max_detections
        self._max_polygon_points = max_polygon_points
        self._max_total_polygon_points = max_total_polygon_points
        self._model: Any | None = None
        self._model_version: str | None = None
        self._load_lock = threading.Lock()
        self._inference_lock = threading.Lock()

    @staticmethod
    def _load_ultralytics_model(model_path: str) -> Any:
        from ultralytics import YOLO

        return YOLO(model_path)

    def _ensure_model(self) -> tuple[Any, str]:
        if self._model is not None and self._model_version is not None:
            return self._model, self._model_version

        with self._load_lock:
            if self._model is not None and self._model_version is not None:
                return self._model, self._model_version
            if not self._model_path.is_file():
                raise ModelNotAvailableError("MODEL_PATH does not point to a readable local weights file.")

            try:
                digest = hashlib.sha256()
                with self._model_path.open("rb") as weights:
                    for chunk in iter(lambda: weights.read(1024 * 1024), b""):
                        digest.update(chunk)
                model = self._model_loader(str(self._model_path))
            except ModelNotAvailableError:
                raise
            except Exception as exc:
                raise ModelNotAvailableError("The local YOLO weights could not be loaded.") from exc

            task = getattr(model, "task", None) or getattr(getattr(model, "model", None), "task", None)
            if task != "segment":
                raise ModelNotAvailableError("MODEL_PATH must contain a YOLO segmentation model.")

            self._model = model
            self._model_version = digest.hexdigest()
            return model, self._model_version

    def predict(self, image: Image.Image, confidence_threshold: float) -> SegmentationResponse:
        model, model_version = self._ensure_model()
        try:
            with self._inference_lock:
                results = model.predict(
                    source=image,
                    conf=confidence_threshold,
                    retina_masks=True,
                    verbose=False,
                )
            if not results or len(results) != 1:
                raise ValueError("YOLO returned an unexpected number of results")
            return self._parse_result(results[0], model_version, image.width, image.height)
        except VisionInferenceError:
            raise
        except Exception as exc:
            raise VisionInferenceError() from exc

    def _parse_result(
        self,
        result: Any,
        model_version: str,
        fallback_width: int,
        fallback_height: int,
    ) -> SegmentationResponse:
        shape = getattr(result, "orig_shape", None)
        if shape is not None and len(shape) >= 2:
            height, width = int(shape[0]), int(shape[1])
        else:
            width, height = fallback_width, fallback_height
        if width <= 0 or height <= 0:
            raise ValueError("YOLO returned invalid image dimensions")

        boxes = getattr(result, "boxes", None)
        if boxes is None:
            return SegmentationResponse(
                modelVersion=model_version,
                width=width,
                height=height,
                detections=[],
            )

        xyxy = _as_numpy(boxes.xyxy)
        confidences = _as_numpy(boxes.conf).reshape(-1)
        classes = _as_numpy(boxes.cls).reshape(-1)
        count = len(confidences)
        if count > self._max_detections:
            raise ValueError("Detection count exceeds the configured response limit")
        if xyxy.shape != (count, 4) or len(classes) != count:
            raise ValueError("YOLO returned inconsistent box arrays")

        masks = getattr(result, "masks", None)
        polygons: Sequence[Any] = [] if masks is None else masks.xy
        if count and len(polygons) != count:
            raise ValueError("Segmentation polygons do not match detected boxes")

        names = getattr(result, "names", None)
        if names is None:
            raise ValueError("YOLO result did not include class names")

        polygon_lengths = [len(polygon) for polygon in polygons]
        if any(length > self._max_polygon_points for length in polygon_lengths):
            raise ValueError("A segmentation polygon exceeds the configured point limit")
        if sum(polygon_lengths) > self._max_total_polygon_points:
            raise ValueError("Segmentation output exceeds the configured total point limit")

        detections: list[Detection] = []
        for index in range(count):
            confidence = _finite_float(confidences[index])
            if not 0.0 <= confidence <= 1.0:
                raise ValueError("YOLO returned an invalid confidence")
            class_id = int(_finite_float(classes[index]))
            try:
                class_name = str(names[class_id]).strip().lower()
            except (KeyError, IndexError, TypeError) as exc:
                raise ValueError("YOLO returned an unknown class id") from exc
            if not class_name or len(class_name) > 64:
                raise ValueError("YOLO returned an invalid class name")

            x1, y1, x2, y2 = (_finite_float(value) for value in xyxy[index])
            x1, x2 = sorted((_clamp(x1, 0.0, float(width)), _clamp(x2, 0.0, float(width))))
            y1, y2 = sorted((_clamp(y1, 0.0, float(height)), _clamp(y2, 0.0, float(height))))
            if x1 >= x2 or y1 >= y2:
                raise ValueError("YOLO returned a bounding box without positive area")
            polygon = _parse_polygon(polygons[index], width, height)
            detections.append(
                Detection(
                    className=class_name,
                    confidence=confidence,
                    bbox=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
                    segmentation=polygon,
                )
            )

        return SegmentationResponse(
            modelVersion=model_version,
            width=width,
            height=height,
            detections=detections,
        )


def _as_numpy(value: Any) -> np.ndarray:
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        value = value.numpy()
    return np.asarray(value)


def _finite_float(value: Any) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("YOLO returned a non-finite value")
    return number


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def _parse_polygon(polygon: Any, width: int, height: int) -> list[list[float]]:
    array = np.asarray(polygon)
    if array.ndim != 2 or array.shape[1] != 2:
        raise ValueError("YOLO returned an invalid segmentation polygon")
    points: list[list[float]] = []
    for x_value, y_value in array:
        x = _clamp(_finite_float(x_value), 0.0, float(width))
        y = _clamp(_finite_float(y_value), 0.0, float(height))
        points.append([x, y])
    return points
