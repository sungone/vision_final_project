import time
from datetime import datetime, timezone

import cv2
import numpy as np

from app.camera import LatestFrameBuffer, LatestValueBuffer
from app.inspection import InspectionEventManager
from app.vision import DEFECT, NORMAL, InspectionResult
from app.vision.worker import VisionWorker


class PixelResultProcessor:
    def process(self, frame: np.ndarray) -> InspectionResult:
        is_defect = int(frame[0, 0, 0]) > 0
        outcome = DEFECT if is_defect else NORMAL
        processed = np.full_like(frame, 210 if is_defect else 80)
        return InspectionResult(
            overall_result=outcome,
            missing_component_result=outcome,
            alignment_result=NORMAL,
            fastening_result=NORMAL,
            metrics={"inferenceTimeMs": 4.2, "detectedInstanceCount": 1},
            processed_frame=processed,
            inspection_time=datetime.now(timezone.utc),
        )


class StepClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        self.value += 1.0
        return self.value


def _event_manager(*, reset_frames: int):
    return InspectionEventManager(
        reset_frames=reset_frames,
        sample_fps=1.0,
        geometry_tolerance_ratio=0.05,
        clock=StepClock(),
    )


def _worker(event_manager, callback):
    raw = LatestFrameBuffer()
    processed = LatestFrameBuffer()
    encoded = LatestValueBuffer[bytes]()
    latest = LatestValueBuffer[InspectionResult]()
    worker = VisionWorker(
        raw,
        processed,
        encoded,
        latest,
        PixelResultProcessor(),
        event_manager,
        callback,
        fps=100.0,
        jpeg_quality=80,
    )
    return worker, raw, processed, encoded, latest


def _put_and_wait(raw, encoded, value: int, after_version: int):
    raw.put(np.full((32, 48, 3), value, dtype=np.uint8))
    snapshot = encoded.get(after_version=after_version, timeout=2.0)
    assert snapshot is not None
    return snapshot


def test_worker_processes_raw_frame_once_and_updates_latest_jpeg_buffer():
    events = []
    worker, raw, processed, encoded, latest = _worker(
        _event_manager(reset_frames=1), events.append
    )
    worker.start()
    try:
        jpeg = _put_and_wait(raw, encoded, 0, 0)
        assert jpeg.value.startswith(b"\xff\xd8")
        assert jpeg.value.endswith(b"\xff\xd9")
        decoded = cv2.imdecode(np.frombuffer(jpeg.value, dtype=np.uint8), cv2.IMREAD_COLOR)
        assert decoded.shape == (32, 48, 3)
        assert processed.version == 1
        assert latest.get(timeout=0).value.overall_result == NORMAL
        assert events == []
    finally:
        worker.stop()
    assert worker.running is False


def test_worker_emits_one_event_per_defect_episode():
    events = []
    manager = _event_manager(reset_frames=2)
    worker, raw, _, encoded, _ = _worker(manager, events.append)
    worker.start()
    version = 0
    try:
        for value in (1, 1, 1):
            snapshot = _put_and_wait(raw, encoded, value, version)
            version = snapshot.version
        assert len(events) == 1

        for value in (0, 0, 1, 1):
            snapshot = _put_and_wait(raw, encoded, value, version)
            version = snapshot.version
        assert len(events) == 2
    finally:
        worker.stop()


def test_event_callback_failure_does_not_stop_vision_worker():
    callback_calls = []

    def failing_callback(result):
        callback_calls.append(result)
        raise RuntimeError("database unavailable")

    worker, raw, _, encoded, _ = _worker(
        _event_manager(reset_frames=1), failing_callback
    )
    worker.start()
    try:
        first = _put_and_wait(raw, encoded, 1, 0)
        deadline = time.monotonic() + 2.0
        while worker.last_error is None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert "database unavailable" in (worker.last_error or "")

        second = _put_and_wait(raw, encoded, 0, first.version)
        assert second.version > first.version
        assert worker.running is True
        assert len(callback_calls) == 1
    finally:
        worker.stop()
