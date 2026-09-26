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


def test_same_defect_is_emitted_once():
    clock = FakeClock()
    manager = _manager(clock)
    defect = _defect()

    events = [_sample(manager, clock, defect) for _ in range(4)]

    assert sum(event is not None for event in events) == 1
    assert manager.state == InspectionState.CONFIRMED_DEFECT


def test_different_defect_is_emitted_without_normal_between():
    clock = FakeClock()
    manager = _manager(clock)
    defect_a = _defect()
    defect_b = _defect(bolt_count=0, reasons=("no_bolt",))

    events = [
        _sample(manager, clock, defect_a),
        _sample(manager, clock, defect_a),
        _sample(manager, clock, defect_b),
        _sample(manager, clock, defect_b),
    ]

    assert [event for event in events if event is not None] == [defect_a, defect_b]


def test_small_segmentation_jitter_is_same_defect():
    clock = FakeClock()
    manager = _manager(clock, tolerance=0.05)

    events = [
        _sample(manager, clock, _defect(thread_length=180.0)),
        _sample(manager, clock, _defect(thread_length=182.0)),
        _sample(manager, clock, _defect(thread_length=179.0)),
    ]

    assert sum(event is not None for event in events) == 1


def test_detection_array_order_does_not_change_signature():
    clock = FakeClock()
    manager = _manager(clock)
    first = _defect()
    reordered = _defect()
    reordered.metrics["detections"] = list(reversed(reordered.metrics["detections"]))

    assert _sample(manager, clock, first) is not None
    assert _sample(manager, clock, reordered) is None


def test_large_relative_position_change_is_new_defect():
    clock = FakeClock()
    manager = _manager(clock, tolerance=0.05)

    first = _sample(manager, clock, _defect(washer_y=150.0))
    second = _sample(manager, clock, _defect(washer_y=280.0))

    assert first is not None
    assert second is not None


def test_categorical_defect_change_is_new_event():
    clock = FakeClock()
    manager = _manager(clock)

    missing_washer = _sample(
        manager,
        clock,
        _defect(washer_count=0, reasons=("washer_low(0)",)),
    )
    no_bolt = _sample(
        manager,
        clock,
        _defect(bolt_count=0, reasons=("no_bolt", "washer_low(0)"), washer_count=0),
    )

    assert missing_washer is not None
    assert no_bolt is not None


def test_normal_reset_allows_same_defect_in_new_cycle():
    clock = FakeClock()
    manager = _manager(clock, reset_frames=2)
    defect = _defect()

    first = _sample(manager, clock, defect)
    assert _sample(manager, clock, _normal()) is None
    assert _sample(manager, clock, _normal()) is None
    assert manager.state == InspectionState.NORMAL
    second = _sample(manager, clock, defect)

    assert first is not None
    assert second is not None


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

    assert sum(event is not None for event in events) == 2


def test_failed_event_delivery_rearms_signature_for_retry():
    clock = FakeClock()
    manager = _manager(clock)
    defect = _defect()

    assert manager.consume(defect) is not None
    manager.mark_event_delivery_failed()
    clock.advance(0.5)
    assert manager.consume(defect) is None
    clock.advance(0.5)
    assert manager.consume(defect) is not None
