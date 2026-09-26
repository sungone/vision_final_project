from __future__ import annotations

import atexit
import logging
import threading

from flask import Flask

from app.camera import CameraCaptureWorker, LatestFrameBuffer, LatestValueBuffer
from app.inspection import InspectionEventManager, InspectionPersistenceWorker, InspectionService
from app.repositories import InspectionRepository
from app.vision.contracts import InspectionResult
from app.vision.decision_engine import InspectionDecisionEngine
from app.vision.mask_rcnn import (
    MaskRCNNPredictor,
    MaskRCNNVisionProcessor,
    MockVisionProcessor,
    SegmentationPostProcessor,
)
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
        self.model_type: str | None = None
        self.model_error: str | None = None
        self.vision_device: str | None = None
        self._started = False
        self._lock = threading.Lock()

        self.event_manager = InspectionEventManager(
            reset_frames=app.config["NORMAL_RESET_FRAMES"],
            sample_fps=app.config["EVENT_SAMPLE_FPS"],
            geometry_tolerance_ratio=app.config["DEFECT_GEOMETRY_TOLERANCE_RATIO"],
        )
        self.persistence = InspectionPersistenceWorker(
            self._persist_event,
            queue_size=app.config["PERSISTENCE_QUEUE_SIZE"],
            retry_seconds=app.config["PERSISTENCE_RETRY_SECONDS"],
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
            self.persistence.submit,
            app.config["VISION_FPS"],
            app.config["JPEG_QUALITY"],
        )

    def _build_processor(self):
        processor_type = self.app.config["VISION_PROCESSOR"]
        if processor_type == "mock":
            self.model_type = "mock"
            return MockVisionProcessor()
        try:
            if processor_type == "unet":
                return self._build_unet_processor()
            if processor_type == "yolo26":
                return self._build_yolo26_processor()
            if processor_type != "mask_rcnn":
                raise ValueError(f"unsupported VISION_PROCESSOR: {processor_type}")
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
                self._build_decision_engine(),
                InspectionVisualizer(
                    self.app.config["MASK_OVERLAY_ALPHA"],
                    self.app.config["DRAW_BOUNDING_BOXES"],
                    self.app.config["DRAW_INFERENCE_STATS"],
                ),
            )
            self.model_loaded = True
            self.model_type = "mask_rcnn"
            self.vision_device = processor.device_name
            return processor
        except Exception as exc:
            self.model_error = str(exc)
            if not self.app.config["ALLOW_MOCK_FALLBACK"]:
                raise RuntimeError(f"vision model could not be loaded: {exc}") from exc
            self.model_type = "mock-fallback"
            logger.exception("vision model could not be loaded; using mock processor")
            return MockVisionProcessor()

    def _build_yolo26_processor(self):
        from app.vision.yolo26 import (
            YOLO26SegPredictor,
            YOLO26SegmentationPostProcessor,
            YOLO26VisionProcessor,
        )

        predictor = YOLO26SegPredictor(
            self.app.config["YOLO26_MODEL_PATH"],
            self.app.config["VISION_DEVICE"],
            self.app.config["YOLO_IMAGE_SIZE"],
            self.app.config["YOLO_SCORE_THRESHOLD"],
            self.app.config["YOLO_IOU_THRESHOLD"],
            self.app.config["YOLO_MAX_DETECTIONS"],
            self.app.config["YOLO_USE_HALF"],
        )
        processor = YOLO26VisionProcessor(
            predictor,
            YOLO26SegmentationPostProcessor(
                predictor.label_to_name,
                self.app.config["MASK_BINARY_THRESHOLD"],
            ),
            self._build_decision_engine(),
            InspectionVisualizer(
                self.app.config["MASK_OVERLAY_ALPHA"],
                self.app.config["DRAW_BOUNDING_BOXES"],
                self.app.config["DRAW_INFERENCE_STATS"],
            ),
        )
        self.model_loaded = True
        self.model_type = "yolo26-seg"
        self.vision_device = processor.device_name
        return processor

    def _build_unet_processor(self):
        from app.vision.unet import (
            UNetSegPredictor,
            UNetSegmentationPostProcessor,
            UNetVisionProcessor,
        )

        predictor = UNetSegPredictor(
            self.app.config["UNET_FINE_MODEL_PATH"],
            self.app.config["UNET_LOCATOR_MODEL_PATH"],
            self.app.config["VISION_DEVICE"],
            self.app.config["UNET_IMAGE_SIZE"],
            self.app.config["UNET_ROI_MARGIN_RATIO"],
            self.app.config["UNET_USE_LOCATOR"],
            self.app.config["UNET_USE_HALF"],
        )
        processor = UNetVisionProcessor(
            predictor,
            UNetSegmentationPostProcessor(
                predictor.label_to_name,
                self.app.config["UNET_MIN_COMPONENT_AREA"],
            ),
            self._build_decision_engine(),
            InspectionVisualizer(
                self.app.config["MASK_OVERLAY_ALPHA"],
                self.app.config["DRAW_BOUNDING_BOXES"],
                self.app.config["DRAW_INFERENCE_STATS"],
            ),
        )
        self.model_loaded = True
        self.model_type = "u-net-resnet18"
        self.vision_device = processor.device_name
        return processor

    def _build_decision_engine(self) -> InspectionDecisionEngine:
        return InspectionDecisionEngine(
            expected_washer_count=self.app.config["EXPECTED_WASHER_COUNT"],
            reference_head_cm=self.app.config["REFERENCE_HEAD_CM"],
            full_thread_cm=self.app.config["FULL_THREAD_CM"],
            tightness_min_ratio=self.app.config["TIGHTNESS_MIN_RATIO"],
        )

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True
            self.persistence.start()
            self.camera.start()
            self.vision.start()

    def stop(self) -> None:
        with self._lock:
            if not self._started:
                return
            self.vision.stop()
            self.camera.stop()
            self.persistence.stop()
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
            raise


def install_runtime(app: Flask) -> Runtime:
    runtime = Runtime(app)
    app.extensions["vision_runtime"] = runtime
    atexit.register(runtime.stop)
    if app.config["START_BACKGROUND_WORKERS"]:
        runtime.start()
    return runtime
