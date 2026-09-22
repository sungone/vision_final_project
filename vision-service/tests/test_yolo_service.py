from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image

from inference.errors import ModelNotAvailableError, VisionInferenceError
from inference.yolo_service import YoloSegmentationService


class FakeModel:
    task = "segment"

    def __init__(self, result: object | None = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls: list[dict[str, object]] = []

    def predict(self, **kwargs: object) -> list[object]:
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return [self.result]


def _result() -> object:
    return SimpleNamespace(
        orig_shape=(100, 200),
        names={0: "bolt", 1: "washer"},
        boxes=SimpleNamespace(
            xyxy=np.array([[-1.0, 2.0, 50.0, 101.0], [20.0, 30.0, 40.0, 60.0]]),
            conf=np.array([0.91, 0.82]),
            cls=np.array([0.0, 1.0]),
        ),
        masks=SimpleNamespace(
            xy=[
                np.array([[-1.0, 2.0], [50.0, 101.0], [25.0, 40.0]]),
                np.array([[20.0, 30.0], [40.0, 30.0], [40.0, 60.0]]),
            ]
        ),
    )


def test_lazy_load_hash_and_parse_complete_polygons(tmp_path: Path) -> None:
    weights = tmp_path / "best.pt"
    weights.write_bytes(b"local-segmentation-weights")
    model = FakeModel(_result())
    loads: list[str] = []

    def loader(path: str) -> FakeModel:
        loads.append(path)
        return model

    service = YoloSegmentationService(weights, model_loader=loader)
    image = Image.new("RGB", (200, 100))

    first = service.predict(image, 0.25)
    second = service.predict(image, 0.50)

    assert loads == [str(weights)]
    assert first.modelVersion == hashlib.sha256(weights.read_bytes()).hexdigest()
    assert second.modelVersion == first.modelVersion
    assert first.width == 200
    assert first.height == 100
    assert first.detections[0].bbox.model_dump() == {"x1": 0.0, "y1": 2.0, "x2": 50.0, "y2": 100.0}
    assert first.detections[0].segmentation == [[0.0, 2.0], [50.0, 100.0], [25.0, 40.0]]
    assert model.calls[0]["conf"] == 0.25
    assert model.calls[0]["retina_masks"] is True


def test_missing_weights_never_calls_loader(tmp_path: Path) -> None:
    calls = 0

    def loader(_path: str) -> FakeModel:
        nonlocal calls
        calls += 1
        return FakeModel(_result())

    service = YoloSegmentationService(tmp_path / "missing.pt", model_loader=loader)

    with pytest.raises(ModelNotAvailableError):
        service.predict(Image.new("RGB", (10, 10)), 0.1)

    assert calls == 0


def test_detection_model_is_rejected(tmp_path: Path) -> None:
    weights = tmp_path / "detect.pt"
    weights.write_bytes(b"detect")
    model = FakeModel(_result())
    model.task = "detect"
    service = YoloSegmentationService(weights, model_loader=lambda _path: model)

    with pytest.raises(ModelNotAvailableError):
        service.predict(Image.new("RGB", (10, 10)), 0.1)


def test_inference_exception_is_sanitized(tmp_path: Path) -> None:
    weights = tmp_path / "best.pt"
    weights.write_bytes(b"segment")
    service = YoloSegmentationService(
        weights,
        model_loader=lambda _path: FakeModel(error=RuntimeError("GPU stack details")),
    )

    with pytest.raises(VisionInferenceError) as caught:
        service.predict(Image.new("RGB", (10, 10)), 0.1)

    assert str(caught.value) == "Vision inference failed."


def test_non_finite_coordinates_fail_inference(tmp_path: Path) -> None:
    weights = tmp_path / "best.pt"
    weights.write_bytes(b"segment")
    result = _result()
    result.boxes.xyxy[0][0] = np.nan
    service = YoloSegmentationService(weights, model_loader=lambda _path: FakeModel(result))

    with pytest.raises(VisionInferenceError):
        service.predict(Image.new("RGB", (200, 100)), 0.1)


def test_polygon_point_limit_fails_without_truncation(tmp_path: Path) -> None:
    weights = tmp_path / "best.pt"
    weights.write_bytes(b"segment")
    result = _result()
    result.masks.xy[0] = np.zeros((10_001, 2))
    service = YoloSegmentationService(weights, model_loader=lambda _path: FakeModel(result))

    with pytest.raises(VisionInferenceError):
        service.predict(Image.new("RGB", (200, 100)), 0.1)
