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


BASE_DIR = Path(__file__).resolve().parents[1]


class Config:
    DEBUG = _bool("FLASK_DEBUG", False)
    TESTING = False
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = _int("FLASK_PORT", 5000)

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

