from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from api.main import create_app
from inference.errors import ModelNotAvailableError, VisionInferenceError
from inference.schemas import BoundingBox, Detection, SegmentationResponse
from inference.yolo_service import YoloSegmentationService


def _jpeg_bytes(width: int = 32, height: int = 24) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), color=(20, 40, 60)).save(buffer, format="JPEG")
    return buffer.getvalue()


class StubService:
    def __init__(self, response: SegmentationResponse | None = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[tuple[int, int, float]] = []

    def predict(self, image: Image.Image, confidence_threshold: float) -> SegmentationResponse:
        self.calls.append((image.width, image.height, confidence_threshold))
        if self.error:
            raise self.error
        assert self.response is not None
        return self.response


def _client(service: StubService) -> TestClient:
    app = create_app()
    app.state.inference_service = service
    return TestClient(app)


def test_segmentation_contract_and_default_threshold() -> None:
    service = StubService(
        SegmentationResponse(
            modelVersion="a" * 64,
            width=32,
            height=24,
            detections=[
                Detection(
                    className="bolt",
                    confidence=0.97,
                    bbox=BoundingBox(x1=1, y1=2, x2=20, y2=22),
                    segmentation=[[1, 2], [20, 2], [20, 22]],
                )
            ],
        )
    )

    response = _client(service).post(
        "/internal/v1/infer/segmentation",
        files={"image": ("sample.jpg", _jpeg_bytes(), "image/jpeg")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "modelVersion": "a" * 64,
        "width": 32,
        "height": 24,
        "detections": [
            {
                "className": "bolt",
                "confidence": 0.97,
                "bbox": {"x1": 1.0, "y1": 2.0, "x2": 20.0, "y2": 22.0},
                "segmentation": [[1.0, 2.0], [20.0, 2.0], [20.0, 22.0]],
            }
        ],
    }
    assert service.calls == [(32, 24, 0.01)]


def test_custom_confidence_is_forwarded() -> None:
    service = StubService(SegmentationResponse(modelVersion="v", width=32, height=24, detections=[]))
    response = _client(service).post(
        "/internal/v1/infer/segmentation",
        files={"image": ("sample.jpg", _jpeg_bytes(), "image/jpeg")},
        data={"confidenceThreshold": "0.35"},
    )

    assert response.status_code == 200
    assert service.calls == [(32, 24, 0.35)]


def test_rejects_mime_magic_mismatch() -> None:
    response = _client(StubService()).post(
        "/internal/v1/infer/segmentation",
        files={"image": ("sample.jpg", b"not-an-image", "image/jpeg")},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_IMAGE"


def test_rejects_oversized_upload() -> None:
    app = create_app()
    app.state.max_image_bytes = 8
    app.state.inference_service = StubService()

    response = TestClient(app).post(
        "/internal/v1/infer/segmentation",
        files={"image": ("sample.jpg", _jpeg_bytes(), "image/jpeg")},
    )

    assert response.status_code == 413
    assert response.json()["code"] == "IMAGE_TOO_LARGE"


def test_invalid_confidence_uses_standard_error_shape() -> None:
    response = _client(StubService()).post(
        "/internal/v1/infer/segmentation",
        files={"image": ("sample.jpg", _jpeg_bytes(), "image/jpeg")},
        data={"confidenceThreshold": "2"},
    )

    assert response.status_code == 422
    assert response.json() == {"code": "INVALID_REQUEST", "message": "The request parameters are invalid."}


def test_optional_service_token_is_enforced() -> None:
    app = create_app()
    app.state.service_token = "secret-token"
    app.state.inference_service = StubService()
    response = TestClient(app).post(
        "/internal/v1/infer/segmentation",
        files={"image": ("sample.jpg", _jpeg_bytes(), "image/jpeg")},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_missing_local_weights_return_model_not_available(tmp_path) -> None:
    app = create_app()
    app.state.inference_service = YoloSegmentationService(tmp_path / "missing.pt")
    response = TestClient(app).post(
        "/internal/v1/infer/segmentation",
        files={"image": ("sample.jpg", _jpeg_bytes(), "image/jpeg")},
    )

    assert response.status_code == 503
    assert response.json()["code"] == "MODEL_NOT_AVAILABLE"


def test_model_unavailable_is_sanitized() -> None:
    response = _client(StubService(error=ModelNotAvailableError())).post(
        "/internal/v1/infer/segmentation",
        files={"image": ("sample.jpg", _jpeg_bytes(), "image/jpeg")},
    )

    assert response.status_code == 503
    assert response.json() == {
        "code": "MODEL_NOT_AVAILABLE",
        "message": "The segmentation model is not available.",
    }


def test_inference_failure_is_sanitized() -> None:
    response = _client(StubService(error=VisionInferenceError())).post(
        "/internal/v1/infer/segmentation",
        files={"image": ("sample.jpg", _jpeg_bytes(), "image/jpeg")},
    )

    assert response.status_code == 500
    assert response.json() == {"code": "VISION_INFERENCE_FAILED", "message": "Vision inference failed."}
