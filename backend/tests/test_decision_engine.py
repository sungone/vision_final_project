from datetime import datetime, timezone

import numpy as np

from app.vision.contracts import DEFECT, NORMAL, NOT_EVALUATED, DetectedInstance, FrameVisionResult
from app.vision.decision_engine import InspectionDecisionEngine
from app.vision.visualizer import InspectionVisualizer


def _instance(class_id: int, class_name: str, y1: int, y2: int) -> DetectedInstance:
    mask = np.zeros((420, 640), dtype=bool)
    mask[y1:y2, 10:30] = True
    return DetectedInstance(
        class_id=class_id,
        class_name=class_name,
        confidence=0.95,
        bbox=(10, y1, 30, y2),
        mask=mask,
        contour=None,
        center=(20.0, (y1 + y2) / 2.0),
        area_px=int(np.count_nonzero(mask)),
    )


def _vision(thread_end: int = 410, *, include_second_washer: bool = True) -> FrameVisionResult:
    instances = [
        _instance(0, "bolt", 0, 90),
        _instance(1, "washer", 90, 115),
        _instance(0, "bolt", 140, 230),
        _instance(2, "thread", 230, thread_end),
    ]
    if include_second_washer:
        instances.insert(2, _instance(1, "washer", 115, 140))
    return FrameVisionResult(datetime.now(timezone.utc), instances, 12.3)


def test_decision_logic_reference_sample_uses_canonical_threshold():
    engine = InspectionDecisionEngine()
    result = engine.evaluate(_vision(), model_type="test")

    assert engine.reference_head_cm == 1.0
    assert engine.reference_nut_cm == 1.0
    assert engine.reference_washer_cm == 0.3
    assert engine.full_thread_cm == 2.0
    assert engine.tightness_min_ratio == 1.08
    assert result.overall_result == DEFECT
    assert result.assembly_sequence_result == NORMAL
    assert result.fastening_quality_result == DEFECT
    assert result.metrics["measuredThreadCm"] == 2.0
    assert result.metrics["threadThresholdCm"] == 2.16
    assert result.metrics["detections"][0] == {
        "classId": 0,
        "className": "bolt",
        "confidence": 0.95,
        "bbox": [10, 0, 30, 90],
        "center": [20.0, 45.0],
        "areaPx": 1800,
    }
    assert "mask" not in result.metrics["detections"][0]
    assert "contour" not in result.metrics["detections"][0]
    assert result.to_live_dict()["assemblySequenceResult"] == NORMAL
    assert result.to_live_dict()["fasteningQualityResult"] == DEFECT


def test_missing_washer_skips_fastening_measurement():
    result = InspectionDecisionEngine().evaluate(
        _vision(include_second_washer=False),
        model_type="test",
    )

    assert result.overall_result == DEFECT
    assert result.assembly_sequence_result == DEFECT
    assert result.fastening_quality_result == NOT_EVALUATED
    assert result.metrics["assemblyReasons"] == ["washer_low(1)"]
    assert result.metrics["fasteningEvaluated"] is False
    assert "measuredThreadCm" not in result.metrics


def test_short_exposed_thread_is_fastening_defect():
    result = InspectionDecisionEngine().evaluate(
        _vision(thread_end=310),
        model_type="test",
    )

    assert result.overall_result == DEFECT
    assert result.assembly_sequence_result == NORMAL
    assert result.fastening_quality_result == DEFECT
    assert result.metrics["measuredThreadCm"] < result.metrics["threadThresholdCm"]


def test_visualizer_draws_decision_panel_on_processed_frame():
    vision = _vision()
    decision = InspectionDecisionEngine().evaluate(vision, model_type="test")
    frame = np.zeros((420, 640, 3), dtype=np.uint8)

    rendered = InspectionVisualizer(draw_boxes=False, draw_stats=False).render(frame, vision, decision)

    assert np.count_nonzero(rendered[-78:]) > 0
    assert np.count_nonzero(frame) == 0
