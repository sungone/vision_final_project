from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from typing import Callable

import cv2

from app.camera.frame_buffer import LatestFrameBuffer, LatestValueBuffer
from app.inspection.event_manager import InspectionEventManager

from .contracts import InspectionResult, VisionProcessor


logger = logging.getLogger(__name__)


class VisionWorker:
    def __init__(
        self,
        raw_frames: LatestFrameBuffer,
        processed_frames: LatestFrameBuffer,
        encoded_frames: LatestValueBuffer[bytes],
        latest_results: LatestValueBuffer[InspectionResult],
        processor: VisionProcessor,
        event_manager: InspectionEventManager,
        event_callback: Callable[[InspectionResult], None],
        fps: float,
        jpeg_quality: int,
    ) -> None:
        self.raw_frames = raw_frames
        self.processed_frames = processed_frames
        self.encoded_frames = encoded_frames
        self.latest_results = latest_results
        self.processor = processor
        self.event_manager = event_manager
        self.event_callback = event_callback
        self.fps = max(0.1, fps)
        self.jpeg_quality = jpeg_quality
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.running = False
        self.last_processed_at: datetime | None = None
        self.last_inference_time_ms: float | None = None
        self.last_detection_count: int | None = None
        self.last_error: str | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="vision-worker", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 3.0) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive() and threading.current_thread() is not self._thread:
            self._thread.join(timeout)

    def _run(self) -> None:
        self.running = True
        last_version = 0
        interval = 1.0 / self.fps
        next_allowed = 0.0
        try:
            while not self._stop.is_set():
                wait = next_allowed - time.monotonic()
                if wait > 0 and self._stop.wait(wait):
                    break
                snapshot = self.raw_frames.get(after_version=last_version, timeout=0.5)
                if snapshot is None:
                    continue
                last_version = snapshot.version
                next_allowed = time.monotonic() + interval
                try:
                    result = self.processor.process(snapshot.value)
                    if result.processed_frame is None:
                        result.processed_frame = snapshot.value
                    ok, encoded = cv2.imencode(
                        ".jpg", result.processed_frame, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
                    )
                    if not ok:
                        raise RuntimeError("JPEG encoding failed")
                    self.processed_frames.put(result.processed_frame, result.inspection_time)
                    self.encoded_frames.put(encoded.tobytes(), result.inspection_time)
                    self.latest_results.put(result, result.inspection_time)
                    self.last_processed_at = result.inspection_time
                    self.last_inference_time_ms = result.metrics.get("inferenceTimeMs")
                    self.last_detection_count = result.metrics.get("detectedInstanceCount")
                    self.last_error = None
                    event = self.event_manager.consume(result)
                    if event is not None:
                        try:
                            self.event_callback(event)
                        except Exception:
                            self.event_manager.mark_event_delivery_failed()
                            raise
                except Exception as exc:
                    self.last_error = str(exc)
                    logger.exception("vision frame processing failed")
        finally:
            self.running = False
