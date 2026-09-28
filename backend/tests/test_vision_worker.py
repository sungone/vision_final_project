from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from app.camera import LatestFrameBuffer, LatestValueBuffer
from app.vision import InspectionResult
from app.vision.worker import VisionWorker


class _Processor:
    def process(self, frame: np.ndarray) -> InspectionResult:
        return InspectionResult(
            processed_frame=frame,
            inspection_time=datetime.now(timezone.utc),
            metrics={"inferenceTimeMs": 4.2, "detectedInstanceCount": 0},
        )


class _EventManager:
    def __init__(self) -> None:
        self.consumed: list[InspectionResult] = []

    def consume(self, result: InspectionResult):
        self.consumed.append(result)
        return None


class _LogProbe:
    def __init__(self, latest_results: LatestValueBuffer[InspectionResult]) -> None:
        self.latest_results = latest_results
        self.logged: list[InspectionResult] = []

    def maybe_log(self, result: InspectionResult) -> bool:
        snapshot = self.latest_results.get(timeout=0)
        assert snapshot is not None
        assert snapshot.value is result
        self.logged.append(result)
        return True


class _FailingLogProbe:
    def maybe_log(self, result: InspectionResult) -> bool:
        raise RuntimeError("console unavailable")


def test_worker_enriches_and_logs_same_result_after_latest_buffer_put():
    raw_frames = LatestFrameBuffer()
    processed_frames = LatestFrameBuffer()
    encoded_frames: LatestValueBuffer[bytes] = LatestValueBuffer()
    latest_results: LatestValueBuffer[InspectionResult] = LatestValueBuffer()
    events = _EventManager()
    worker = VisionWorker(
        raw_frames,
        processed_frames,
        encoded_frames,
        latest_results,
        _Processor(),
        events,  # type: ignore[arg-type]
        lambda result: None,
        fps=100.0,
        jpeg_quality=80,
    )
    probe = _LogProbe(latest_results)
    worker.live_result_logger = probe  # type: ignore[assignment]

    worker.start()
    try:
        raw_frames.put(np.zeros((16, 16, 3), dtype=np.uint8))
        first = latest_results.get(after_version=0, timeout=2.0)
        assert first is not None
        raw_frames.put(np.ones((16, 16, 3), dtype=np.uint8))
        second = latest_results.get(after_version=first.version, timeout=2.0)
        assert second is not None
    finally:
        worker.stop()

    assert second.value.metrics["processingTimeMs"] >= 0
    assert second.value.metrics["visionFps"] > 0
    assert probe.logged[-1] is second.value
    assert events.consumed[-1] is second.value


def test_live_log_failure_does_not_block_event_manager():
    raw_frames = LatestFrameBuffer()
    latest_results: LatestValueBuffer[InspectionResult] = LatestValueBuffer()
    events = _EventManager()
    worker = VisionWorker(
        raw_frames,
        LatestFrameBuffer(),
        LatestValueBuffer(),
        latest_results,
        _Processor(),
        events,  # type: ignore[arg-type]
        lambda result: None,
        fps=100.0,
        jpeg_quality=80,
    )
    worker.live_result_logger = _FailingLogProbe()  # type: ignore[assignment]

    worker.start()
    try:
        raw_frames.put(np.zeros((16, 16, 3), dtype=np.uint8))
        snapshot = latest_results.get(after_version=0, timeout=2.0)
        assert snapshot is not None
        for _ in range(100):
            if events.consumed:
                break
            worker._stop.wait(0.01)
    finally:
        worker.stop()

    assert events.consumed[-1] is snapshot.value
