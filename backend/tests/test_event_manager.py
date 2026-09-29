from __future__ import annotations

import numpy as np

from app.inspection import InspectionEventManager, InspectionState
from app.vision import DEFECT, NORMAL, NOT_EVALUATED, InspectionResult


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float = 1.0) -> None:
        self.value += seconds


def _manager(clock: FakeClock, *, reset_frames: int = 2, tolerance: float = 0.05):
    return InspectionEventManager(
        reset_frames=reset_frames,
        sample_fps=1.0,
        geometry_tolerance_ratio=tolerance,
        clock=clock,
    )


def _normal() -> InspectionResult:
    return InspectionResult(overall_result=NORMAL)


def _defect(
    *,
    bolt_count: int = 2,
    washer_count: int = 1,
    thread_count: int = 1,
    reasons: tuple[str, ...] = ("washer_low(1)",),
    washer_y: float = 160.0,
    thread_length: float = 180.0,
) -> InspectionResult:
    detections: list[dict] = []
    for index in range(bolt_count):
        y = 40.0 if index == 0 else 220.0
        detections.append(_detection("bolt", index, 300.0, y, 80.0, 60.0))
    for index in range(washer_count):
        detections.append(_detection("washer", index, 300.0, washer_y + index * 30.0, 100.0, 24.0))
    for index in range(thread_count):
        detections.append(_detection("thread", index, 300.0, 260.0, 42.0, thread_length))

    counts = {"bolt": bolt_count, "thread": thread_count, "washer": washer_count}
    return InspectionResult(
        overall_result=DEFECT,
        missing_component_result=DEFECT,
        alignment_result=NOT_EVALUATED,
        fastening_result=NOT_EVALUATED,
        metrics={
            "detectedCounts": counts,
            "assemblyReasons": list(reasons),
            "detections": detections,
            "inferenceTimeMs": 12.3,
        },
        processed_frame=np.zeros((480, 640, 3), dtype=np.uint8),
    )


def _detection(
    class_name: str,
    class_id: int,
    center_x: float,
    center_y: float,
    width: float,
    height: float,
) -> dict:
    return {
        "classId": class_id,
        "className": class_name,
        "confidence": 0.95,
        "bbox": [
            center_x - width / 2,
            center_y - height / 2,
            center_x + width / 2,
            center_y + height / 2,
        ],
        "center": [center_x, center_y],
        "areaPx": width * height,
    }


def _sample(manager, clock: FakeClock, result: InspectionResult):
    event = manager.consume(result)
    clock.advance()
    return event


def test_every_sampled_defect_is_emitted():
    clock = FakeClock()
    manager = _manager(clock)
    defect = _defect()

    events = [_sample(manager, clock, defect) for _ in range(4)]

    assert events == [defect, defect, defect, defect]
    assert manager.state == InspectionState.CONFIRMED_DEFECT


def test_every_sampled_normal_is_emitted_without_stability_gate():
    clock = FakeClock()
    manager = _manager(clock, reset_frames=2)
    normal = _normal()

    events = [_sample(manager, clock, normal) for _ in range(4)]

    assert events == [normal, normal, normal, normal]
    assert manager.state == InspectionState.NORMAL


def test_result_changes_are_not_required_for_emission():
    clock = FakeClock()
    manager = _manager(clock)
    defect_a = _defect()
    defect_b = _defect(bolt_count=0, reasons=("no_bolt",))
    normal = _normal()

    events = [
        _sample(manager, clock, defect_a),
        _sample(manager, clock, defect_a),
        _sample(manager, clock, normal),
        _sample(manager, clock, defect_b),
    ]

    assert events == [defect_a, defect_a, normal, defect_b]
    assert manager.state == InspectionState.CONFIRMED_DEFECT


def test_event_evaluation_does_not_exceed_sample_fps():
    clock = FakeClock()
    manager = _manager(clock)
    defect_a = _defect()
    defect_b = _defect(bolt_count=0, reasons=("no_bolt",))

    events = [manager.consume(defect_a)]
    for _ in range(9):
        clock.advance(0.1)
        events.append(manager.consume(defect_b))
    clock.value = 1.0
    events.append(manager.consume(defect_b))

    assert [event for event in events if event is not None] == [defect_a, defect_b]


def test_failed_event_delivery_keeps_fixed_sampling_schedule():
    clock = FakeClock()
    manager = _manager(clock)
    defect = _defect()

    assert manager.consume(defect) is not None
    manager.mark_event_delivery_failed()
    clock.advance(0.5)
    assert manager.consume(defect) is None
    clock.advance(0.5)
    assert manager.consume(defect) is not None
