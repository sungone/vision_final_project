from __future__ import annotations

import os
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

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://vision:vision@localhost:5432/vision"
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
    STREAM_FPS = _float("STREAM_FPS", 10.0)
    JPEG_QUALITY = min(100, max(1, _int("JPEG_QUALITY", 80)))
    VISION_PROCESSOR = os.getenv("VISION_PROCESSOR", "yolo26").strip().lower()
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
    YOLO26_MODEL_PATH = _path(
        "YOLO26_MODEL_PATH", PROJECT_DIR / "output" / "yolo26" / "best.pt", BASE_DIR
    )
    YOLO_IMAGE_SIZE = max(32, _int("YOLO_IMAGE_SIZE", 640))
    YOLO_SCORE_THRESHOLD = min(1.0, max(0.0, _float("YOLO_SCORE_THRESHOLD", 0.7)))
    YOLO_IOU_THRESHOLD = min(1.0, max(0.0, _float("YOLO_IOU_THRESHOLD", 0.7)))
    YOLO_MAX_DETECTIONS = max(1, _int("YOLO_MAX_DETECTIONS", 100))
    YOLO_USE_HALF = _bool("YOLO_USE_HALF", True)

    DEFECT_CONFIRM_FRAMES = max(1, _int("DEFECT_CONFIRM_FRAMES", 3))
    NORMAL_RESET_FRAMES = max(1, _int("NORMAL_RESET_FRAMES", 5))
    EVENT_COOLDOWN_SECONDS = max(0.0, _float("EVENT_COOLDOWN_SECONDS", 1.0))

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
