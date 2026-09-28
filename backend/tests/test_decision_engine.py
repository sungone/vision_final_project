from datetime import datetime, timezone

import numpy as np
import pytest

from app.vision.contracts import DEFECT, NORMAL, NOT_EVALUATED, DetectedInstance, FrameVisionResult
from app.vision.decision_engine import (
    AssignedRoles,
    InspectionDecisionEngine,
    ProjectedInstance,
)
from app.vision.live_result_logger import format_live_inspection


SHAPE = (100, 240)


def _instance(class_id: int, class_name: str, x1: int, x2: int, y1: int = 35, y2: int = 65):
    mask = np.zeros(SHAPE, dtype=bool)
    mask[y1:y2, x1:x2] = True
    return DetectedInstance(
        class_id,
        class_name,
        0.95,
        (x1, y1, x2, y2),
        mask,
        None,
        ((x1 + x2 - 1) / 2.0, (y1 + y2 - 1) / 2.0),
        int(np.count_nonzero(mask)),
    )


def _vision(*, thread_end: int = 190, instances=None) -> FrameVisionResult:
    if instances is None:
        instances = [
            _instance(0, "bolt", 0, 40),
            _instance(1, "washer", 45, 55, 30, 70),
            _instance(1, "washer", 60, 70, 30, 70),
            _instance(0, "bolt", 75, 105, 25, 75),
            _instance(2, "thread", 105, thread_end, 40, 60),
        ]
    return FrameVisionResult(datetime.now(timezone.utc), instances, 12.3)


def test_normal_sample_uses_axis_geometry_and_threshold():
    result = InspectionDecisionEngine().evaluate(_vision(), model_type="test")

    assert result.overall_result == NORMAL
    assert result.missing_component_result == NORMAL
    assert result.alignment_result == NORMAL
    assert result.assembly_sequence_result == NORMAL
    assert result.fastening_result == NORMAL
    assert result.metrics["threadExposureRatio"] >= 1.36
    assert result.metrics["threadExposureThreshold"] == 1.36
    assert result.metrics["nutWasherGapRatio"] > 0
    assert result.metrics["nutTiltDeg"] == pytest.approx(0.0, abs=0.1)
    assert result.metrics["reasons"] == []


def test_largest_thread_is_used_and_multiple_threads_are_not_a_defect():
    instances = _vision().instances + [_instance(2, "thread", 200, 205, 45, 55)]

    result = InspectionDecisionEngine().evaluate(_vision(instances=instances), model_type="test")

    assert result.overall_result == NORMAL
    assert result.metrics["detectedCounts"]["thread"] == 2
    assert result.metrics["threadExposureRatio"] > 1.36
    assert result.metrics["reasons"] == []


def test_thread_missing_stops_with_unavailable_measurements():
    result = InspectionDecisionEngine().evaluate(
        _vision(instances=[item for item in _vision().instances if item.class_name != "thread"]),
        model_type="test",
    )

    assert result.overall_result == DEFECT
    assert result.missing_component_result == DEFECT
    assert result.alignment_result == NOT_EVALUATED
    assert result.fastening_result == NOT_EVALUATED
    assert result.metrics["reasons"] == ["THREAD_MISSING"]
    assert result.metrics["threadExposureThreshold"] == 1.36
    assert result.metrics.get("threadExposureRatio") is None
    assert result.metrics.get("nutWasherGapPx") is None
    assert result.metrics.get("nutTiltDeg") is None


def test_one_bolt_accumulates_component_and_fastening_reasons():
    instances = [item for item in _vision().instances if not (item.class_name == "bolt" and item.center[0] > 50)]

    result = InspectionDecisionEngine().evaluate(_vision(instances=instances), model_type="test")

    assert result.missing_component_result == DEFECT
    assert result.alignment_result == NOT_EVALUATED
    assert result.fastening_result == DEFECT
    assert result.metrics["reasons"] == ["NUT_MISSING", "FASTEN_UNMEASURED"]


def test_judge_rules_reject_non_two_washer_configuration():
    with pytest.raises(ValueError, match="expected_washer_count=2"):
        InspectionDecisionEngine(expected_washer_count=1)


def test_component_defect_does_not_skip_fastening_and_reasons_accumulate():
    instances = [
        _instance(0, "bolt", 0, 40),
        _instance(1, "washer", 60, 70, 30, 70),
        _instance(0, "bolt", 75, 105, 25, 75),
        _instance(2, "thread", 105, 125, 40, 60),
    ]

    result = InspectionDecisionEngine().evaluate(_vision(instances=instances), model_type="test")

    assert result.missing_component_result == DEFECT
    assert result.alignment_result == NOT_EVALUATED
    assert result.fastening_result == DEFECT
    assert result.metrics["reasons"] == ["WASHER_MISSING_HEAD_SIDE", "LOOSE"]
    assert result.metrics["threadExposureRatio"] < 1.36


def test_remaining_head_side_washer_identifies_missing_nut_side():
    instances = [
        _instance(0, "bolt", 0, 40),
        _instance(1, "washer", 45, 55, 30, 70),
        _instance(0, "bolt", 75, 105, 25, 75),
        _instance(2, "thread", 105, 190, 40, 60),
    ]

    result = InspectionDecisionEngine().evaluate(_vision(instances=instances), model_type="test")

    assert result.metrics["componentReasons"] == ["WASHER_MISSING_NUT_SIDE"]
    assert result.fastening_result == NORMAL
    assert result.metrics["nutWasherGapRatio"] is None


def test_extra_nut_is_component_defect_but_fastening_is_still_measured():
    instances = _vision().instances + [_instance(0, "bolt", 200, 225)]

    result = InspectionDecisionEngine().evaluate(_vision(instances=instances), model_type="test")

    assert result.metrics["componentReasons"] == ["NUT_EXTRA"]
    assert result.alignment_result == NOT_EVALUATED
    assert result.fastening_result == NORMAL
    assert result.metrics["threadExposureRatio"] >= 1.36


def test_unseated_nut_keeps_component_and_order_normal_but_fails_fastening():
    instances = [
        _instance(0, "bolt", 0, 40),
        _instance(1, "washer", 45, 55, 30, 70),
        _instance(1, "washer", 60, 70, 30, 70),
        _instance(2, "thread", 105, 190, 40, 60),
        _instance(0, "bolt", 120, 150),
    ]

    result = InspectionDecisionEngine().evaluate(_vision(instances=instances), model_type="test")

    assert result.missing_component_result == NORMAL
    assert result.alignment_result == NORMAL
    assert result.fastening_result == DEFECT
    assert result.metrics["reasons"] == ["NUT_NOT_SEATED"]
    assert result.metrics.get("threadExposureRatio") is None


def test_wrong_order_is_checked_only_after_component_check_passes():
    instances = [
        _instance(1, "washer", 0, 10, 30, 70),
        _instance(0, "bolt", 15, 45),
        _instance(1, "washer", 60, 70, 30, 70),
        _instance(0, "bolt", 75, 105, 25, 75),
        _instance(2, "thread", 105, 190, 40, 60),
    ]

    result = InspectionDecisionEngine().evaluate(_vision(instances=instances), model_type="test")

    assert result.missing_component_result == NORMAL
    assert result.alignment_result == DEFECT
    assert "ORDER_INVALID" in result.metrics["reasons"]
    assert result.metrics["threadExposureRatio"] >= 1.36


def test_gap_threshold_is_optional_and_tilt_is_measurement_only():
    normal = InspectionDecisionEngine(gap_ratio_max=None).evaluate(_vision(), model_type="test")
    limited = InspectionDecisionEngine(gap_ratio_max=0.01).evaluate(_vision(), model_type="test")

    assert normal.fastening_result == NORMAL
    assert normal.metrics["nutWasherGapRatio"] > 0.01
    assert normal.metrics["nutTiltDeg"] is not None
    assert limited.fastening_result == DEFECT
    assert limited.metrics["fasteningReasons"] == ["GAP"]


def test_thread_and_gap_thresholds_are_inclusive():
    engine = InspectionDecisionEngine(gap_ratio_max=0.5)
    thread_instance = _instance(2, "thread", 100, 120, 40, 60)
    nut_instance = _instance(0, "bolt", 60, 90, 25, 75)
    washer_instance = _instance(1, "washer", 50, 55, 30, 70)
    thread = ProjectedInstance(thread_instance, 0.0, 13.6, 6.8, np.array([[0.0, 0.0]]))
    nut = ProjectedInstance(nut_instance, 0.0, 1.0, 0.5, np.column_stack(np.nonzero(nut_instance.mask)[::-1]))
    washer = ProjectedInstance(washer_instance, -5.0, -5.0, -5.0, np.column_stack(np.nonzero(washer_instance.mask)[::-1]))
    roles = AssignedRoles(nut=nut, nut_side_washers=[washer])

    result = engine.check_fastening(
        thread,
        roles,
        perpendicular=np.array([0.0, 1.0]),
        diameter_px=10.0,
    )

    assert result.thread_ratio == pytest.approx(1.36)
    assert result.gap_ratio == pytest.approx(0.5)
    assert result.result == NORMAL
    assert result.reasons == []


def test_bolt_diameter_converts_ratios_to_mm_without_changing_judgment():
    result = InspectionDecisionEngine(bolt_diameter_mm=10.0).evaluate(
        _vision(), model_type="test"
    )

    assert result.metrics["threadExposureMm"] == pytest.approx(
        result.metrics["threadExposureRatio"] * 10.0, abs=0.001
    )
    assert result.metrics["nutWasherGapMm"] == pytest.approx(
        result.metrics["nutWasherGapRatio"] * 10.0, abs=0.001
    )


def test_live_formatter_uses_the_decision_engine_metrics_without_recalculation():
    result = InspectionDecisionEngine().evaluate(_vision(), model_type="test")

    output = format_live_inspection(result)

    assert f"Thread Exposure Ratio: {result.metrics['threadExposureRatio']:.3f}" in output
    assert f"Threshold            : {result.metrics['threadExposureThreshold']:.3f}" in output
    assert f"Nut-Washer Gap       : {result.metrics['nutWasherGapPx']:.2f} px" in output
    assert f"Nut Tilt             : {result.metrics['nutTiltDeg']:.2f} deg" in output
