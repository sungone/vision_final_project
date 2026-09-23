from __future__ import annotations

import atexit
import logging
import threading

from flask import Flask

from app.camera import CameraCaptureWorker, LatestFrameBuffer, LatestValueBuffer
from app.inspection import InspectionEventManager, InspectionService
from app.repositories import InspectionRepository
from app.vision.contracts import InspectionResult
from app.vision.mask_rcnn_predictor import MaskRCNNPredictor
from app.vision.postprocessor import SegmentationPostProcessor
from app.vision.processor import MaskRCNNVisionProcessor, MockVisionProcessor
from app.vision.visualizer import InspectionVisualizer
from app.vision.worker import VisionWorker


logger = logging.getLogger(__name__)


class Runtime:
    def __init__(self, app: Flask) -> None:
        self.app = app
        self.raw_frames = LatestFrameBuffer()
        self.processed_frames = LatestFrameBuffer()
        self.encoded_frames: LatestValueBuffer[bytes] = LatestValueBuffer()
        self.latest_results: LatestValueBuffer[InspectionResult] = LatestValueBuffer()
        self.last_database_error: str | None = None
        self.model_loaded = False
        self.model_error: str | None = None
        self.vision_device: str | None = None
        self._started = False
        self._lock = threading.Lock()

        self.event_manager = InspectionEventManager(
            app.config["DEFECT_CONFIRM_FRAMES"],
            app.config["NORMAL_RESET_FRAMES"],
            app.config["EVENT_COOLDOWN_SECONDS"],
        )
        self.camera = CameraCaptureWorker(
            self.raw_frames,
            app.config["CAMERA_INDEX"],
            app.config["CAMERA_WIDTH"],
            app.config["CAMERA_HEIGHT"],
            app.config["CAMERA_FPS"],
            app.config["CAMERA_RECONNECT_SECONDS"],
        )
        processor = self._build_processor()
        self.vision = VisionWorker(
            self.raw_frames,
            self.processed_frames,
            self.encoded_frames,
            self.latest_results,
            processor,
            self.event_manager,
            self._persist_event,
            app.config["VISION_FPS"],
            app.config["JPEG_QUALITY"],
        )

    def _build_processor(self):
        if self.app.config["VISION_PROCESSOR"] == "mock":
            return MockVisionProcessor()
        try:
            predictor = MaskRCNNPredictor(
                self.app.config["MASK_RCNN_MODEL_PATH"],
                self.app.config["MASK_RCNN_METADATA_PATH"],
                self.app.config["VISION_DEVICE"],
            )
            processor = MaskRCNNVisionProcessor(
                predictor,
                SegmentationPostProcessor(
                    predictor.label_to_name,
                    self.app.config["MASK_SCORE_THRESHOLD"],
                    self.app.config["MASK_BINARY_THRESHOLD"],
                ),
                InspectionVisualizer(
                    self.app.config["MASK_OVERLAY_ALPHA"],
                    self.app.config["DRAW_BOUNDING_BOXES"],
                    self.app.config["DRAW_INFERENCE_STATS"],
                ),
            )
            self.model_loaded = True
            self.vision_device = processor.device_name
            return processor
        except Exception as exc:
            self.model_error = str(exc)
            logger.exception("Mask R-CNN could not be loaded; using mock processor")
            return MockVisionProcessor()

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True
            self.camera.start()
            self.vision.start()

    def stop(self) -> None:
        with self._lock:
            if not self._started:
                return
            self.vision.stop()
            self.camera.stop()
            self._started = False

    def _persist_event(self, result: InspectionResult) -> None:
        try:
            with self.app.app_context():
                InspectionService(
                    InspectionRepository(), self.app.config["DEFECT_STORAGE_DIR"]
                ).persist_event(result)
            self.last_database_error = None
        except Exception as exc:
            self.last_database_error = str(exc)
            logger.exception("confirmed inspection event could not be persisted")


def install_runtime(app: Flask) -> Runtime:
    runtime = Runtime(app)
    app.extensions["vision_runtime"] = runtime
    atexit.register(runtime.stop)
    if app.config["START_BACKGROUND_WORKERS"]:
        runtime.start()
    return runtime


