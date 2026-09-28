from __future__ import annotations

import os
import math
from pathlib import Path


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _optional_float(name: str) -> float | None:
    value = os.getenv(name)
    if value is None or value.strip().lower() in {"", "none", "null"}:
        return None
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a finite number or null") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{name} must be a finite number or null")
    return parsed


def _strict_float(name: str, default: float) -> float:
    value = os.getenv(name, str(default))
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{name} must be a finite number")
    return parsed


def _path(name: str, default: Path, relative_to: Path) -> str:
    configured = Path(os.getenv(name, str(default)))
    if not configured.is_absolute():
        configured = relative_to / configured
    return str(configured.resolve())


def _list(name: str, default: str = "") -> tuple[str, ...]:
    value = os.getenv(name, default)
    return tuple(item.strip().rstrip("/") for item in value.split(",") if item.strip())


BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BASE_DIR.parent


class Config:
    DEBUG = _bool("FLASK_DEBUG", False)
    TESTING = False
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = _int("FLASK_PORT", 5000)
    CORS_ALLOWED_ORIGINS = _list("CORS_ALLOWED_ORIGINS", "http://localhost:5173")

    MAX_UPLOAD_IMAGE_BYTES = max(
        1,
        _int(
            "MAX_UPLOAD_IMAGE_BYTES",
            10 * 1024 * 1024,
        ),
    )
    MAX_CONTENT_LENGTH = max(
        MAX_UPLOAD_IMAGE_BYTES + 1024 * 1024,
        _int(
            "MAX_UPLOAD_REQUEST_BYTES",
            11 * 1024 * 1024,
        ),
    )

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://vision:vision@localhost:5432/vision_inspection"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 300}
    DATABASE_AUTO_CREATE = _bool("DATABASE_AUTO_CREATE", False)

    CAMERA_INDEX = os.getenv("CAMERA_INDEX", "0")
    CAMERA_WIDTH = _int("CAMERA_WIDTH", 1280)
    CAMERA_HEIGHT = _int("CAMERA_HEIGHT", 720)
    CAMERA_FPS = _float("CAMERA_FPS", 30.0)
    CAMERA_RECONNECT_SECONDS = _float("CAMERA_RECONNECT_SECONDS", 2.0)

    VISION_FPS = _float("VISION_FPS", 10.0)
    VISION_LIVE_CONSOLE = _bool("VISION_LIVE_CONSOLE", False)
    VISION_CONSOLE_REFRESH_FPS = max(
        0.1, _float("VISION_CONSOLE_REFRESH_FPS", 4.0)
    )
    STREAM_FPS = _float("STREAM_FPS", 10.0)
    JPEG_QUALITY = min(100, max(1, _int("JPEG_QUALITY", 80)))
    VISION_PROCESSOR = os.getenv("VISION_PROCESSOR", "unet").strip().lower()
    MASK_RCNN_MODEL_PATH = _path(
        "MASK_RCNN_MODEL_PATH", PROJECT_DIR / "output" / "mask_rcnn" / "mask_rcnn_state_dict.pt", BASE_DIR
    )
    MASK_RCNN_METADATA_PATH = _path(
        "MASK_RCNN_METADATA_PATH", PROJECT_DIR / "output" / "mask_rcnn" / "model_metadata.json", BASE_DIR
    )
    VISION_DEVICE = os.getenv("VISION_DEVICE", "auto")
    MASK_SCORE_THRESHOLD = min(1.0, max(0.0, _float("MASK_SCORE_THRESHOLD", 0.7)))
    MASK_BINARY_THRESHOLD = min(1.0, max(0.0, _float("MASK_BINARY_THRESHOLD", 0.5)))
    MASK_OVERLAY_ALPHA = min(1.0, max(0.0, _float("MASK_OVERLAY_ALPHA", 0.45)))
    DRAW_BOUNDING_BOXES = _bool("DRAW_BOUNDING_BOXES", True)
    DRAW_INFERENCE_STATS = _bool("DRAW_INFERENCE_STATS", True)
    EXPECTED_WASHER_COUNT = max(0, _int("EXPECTED_WASHER_COUNT", 2))
    DECISION_THRESHOLDS_PATH = _path(
        "DECISION_THRESHOLDS_PATH",
        PROJECT_DIR / "U-NET" / "U-NET" / "thresholds.json",
        BASE_DIR,
    )
    THREAD_EXPOSURE_MIN_RATIO = max(
        0.001, _strict_float("THREAD_EXPOSURE_MIN_RATIO", 1.36)
    )
    THREAD_EXPOSURE_MIN_RATIO_FROM_ENV = (
        os.getenv("THREAD_EXPOSURE_MIN_RATIO") is not None
    )
    NUT_WASHER_GAP_MAX_RATIO = _optional_float(
        "NUT_WASHER_GAP_MAX_RATIO"
    )
    NUT_WASHER_GAP_MAX_RATIO_FROM_ENV = (
        os.getenv("NUT_WASHER_GAP_MAX_RATIO") is not None
    )
    BOLT_DIAMETER_MM = _optional_float("BOLT_DIAMETER_MM")
    UNET_FINE_MODEL_PATH = _path(
        "UNET_FINE_MODEL_PATH", PROJECT_DIR / "output" / "u-net" / "fine" / "best.pt", BASE_DIR
    )
    UNET_LOCATOR_MODEL_PATH = _path(
        "UNET_LOCATOR_MODEL_PATH", PROJECT_DIR / "output" / "u-net" / "locator" / "best.pt", BASE_DIR
    )
    UNET_LOCATOR_WIDTH = max(32, _int("UNET_LOCATOR_WIDTH", 512))
    UNET_FINE_SIZE = max(32, _int("UNET_FINE_SIZE", 512))
    UNET_ROI_MARGIN = max(1.0, _float("UNET_ROI_MARGIN", 1.3))
    UNET_ROI_MIN_SIDE = max(1, _int("UNET_ROI_MIN_SIDE", 256))
    UNET_ROI_SMOOTH = min(1.0, max(0.0, _float("UNET_ROI_SMOOTH", 0.5)))
    UNET_USE_LOCATOR = _bool("UNET_USE_LOCATOR", True)
    UNET_MIN_COMPONENT_AREA = max(1, _int("UNET_MIN_COMPONENT_AREA", 150))
    UNET_USE_HALF = _bool("UNET_USE_HALF", True)
    YOLO26_MODEL_PATH = _path(
        "YOLO26_MODEL_PATH", PROJECT_DIR / "output" / "yolo26" / "best.pt", BASE_DIR
    )
    YOLO_IMAGE_SIZE = max(32, _int("YOLO_IMAGE_SIZE", 640))
    YOLO_SCORE_THRESHOLD = min(1.0, max(0.0, _float("YOLO_SCORE_THRESHOLD", 0.7)))
    YOLO_IOU_THRESHOLD = min(1.0, max(0.0, _float("YOLO_IOU_THRESHOLD", 0.7)))
    YOLO_MAX_DETECTIONS = max(1, _int("YOLO_MAX_DETECTIONS", 100))
    YOLO_USE_HALF = _bool("YOLO_USE_HALF", True)

    NORMAL_RESET_FRAMES = max(1, _int("NORMAL_RESET_FRAMES", 5))
    EVENT_SAMPLE_FPS = max(0.001, _float("EVENT_SAMPLE_FPS", 1.0))
    DEFECT_GEOMETRY_TOLERANCE_RATIO = min(
        1.0, max(0.0, _float("DEFECT_GEOMETRY_TOLERANCE_RATIO", 0.05))
    )
    PERSISTENCE_QUEUE_SIZE = max(1, _int("PERSISTENCE_QUEUE_SIZE", 10))
    PERSISTENCE_RETRY_SECONDS = max(0.1, _float("PERSISTENCE_RETRY_SECONDS", 2.0))
    ALLOW_MOCK_FALLBACK = _bool("ALLOW_MOCK_FALLBACK", False)

    DEFECT_STORAGE_DIR = str(
        Path(os.getenv("DEFECT_STORAGE_DIR", str(BASE_DIR / "storage" / "defects"))).resolve()
    )
    START_BACKGROUND_WORKERS = _bool("START_BACKGROUND_WORKERS", True)


class TestConfig(Config):
    TESTING = True
    START_BACKGROUND_WORKERS = False
    DATABASE_AUTO_CREATE = True
    SQLALCHEMY_DATABASE_URI = "sqlite+pysqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
