from datetime import datetime, timezone

import numpy as np

from app.vision.contracts import (
    DEFECT,
    NORMAL,
    NOT_EVALUATED,
    DetectedInstance,
    FrameVisionResult,
)
from app.vision.decision_engine import InspectionDecisionEngine


def _instance(
    class_id: int,
    class_name: str,
    y1: int,
    y2: int,
    x1: int = 20,
    x2: int = 100,
) -> DetectedInstance:
    mask = np.zeros((460, 140), dtype=bool)
    mask[y1:y2, x1:x2] = True
    ys, xs = np.nonzero(mask)
    return DetectedInstance(
        class_id=class_id,
        class_name=class_name,
        confidence=0.95,
        bbox=(x1, y1, x2, y2),
        mask=mask,
        contour=None,
        center=(float(xs.mean()), float(ys.mean())),
        area_px=int(mask.sum()),
    )


def _normal_instances(*, thread_end: int = 360) -> list[DetectedInstance]:
    return [
        _instance(1, "bolt", 50, 100),
        _instance(2, "washer", 120, 130, 10, 110),
        _instance(2, "washer", 150, 160, 10, 110),
        _instance(1, "bolt", 180, 220),
        _instance(3, "thread", 240, thread_end, 35, 85),
    ]


def _evaluate(instances, **engine_kwargs):
    vision = FrameVisionResult(
        datetime.now(timezone.utc), instances, inference_time_ms=12.3
    )
    engine_kwargs.setdefault("thread_ratio_min", 1.36)
    return InspectionDecisionEngine(**engine_kwargs).evaluate(
        vision, model_type="test"
    )


def test_normal_assembly_reports_roles_and_geometry():
    result = _evaluate(_normal_instances())

    assert result.overall_result == NORMAL
    assert result.component_result == NORMAL
    assert result.assembly_sequence_result == NORMAL
    assert result.fastening_quality_result == NORMAL
    assert result.metrics["componentCounts"] == {
        "bolt": 1,
        "nut": 1,
        "upperWasher": 1,
        "lowerWasher": 1,
        "nutSideWasher": 1,
        "headSideWasher": 1,
        "unassignedWasher": 0,
        "thread": 1,
    }
    assert result.metrics["threadExposureRatio"] >= 1.36
    assert result.metrics["threadExposureThreshold"] == 1.36
    assert result.metrics["nutWasherGapPx"] is not None
    assert result.metrics["nutTiltDeg"] is not None
    assert result.metrics["failureReasons"] == []


def test_missing_nut_accumulates_component_and_fastening_reasons():
    instances = [
        item
        for index, item in enumerate(_normal_instances())
        if index != 3
    ]
    instances[2] = _instance(2, "washer", 220, 230, 10, 110)
    result = _evaluate(instances)

    assert result.component_result == DEFECT
    assert result.assembly_sequence_result == NOT_EVALUATED
    assert result.fastening_quality_result == DEFECT
    assert result.metrics["failureReasons"] == [
        "NUT_MISSING",
        "FASTEN_UNMEASURED",
    ]
    assert result.metrics["componentCounts"]["upperWasher"] == 1
    assert result.metrics["componentCounts"]["lowerWasher"] == 1
    assert result.metrics["threadExposureRatio"] is None


def test_missing_nut_and_nut_side_washer_reports_exact_side():
    instances = [
        _instance(1, "bolt", 50, 100),
        _instance(2, "washer", 120, 130, 10, 110),
        _instance(3, "thread", 240, 360, 35, 85),
    ]

    result = _evaluate(instances)

    assert result.metrics["assemblyReasons"] == [
        "NUT_MISSING",
        "WASHER_MISSING_NUT_SIDE",
    ]
    assert result.metrics["componentCounts"]["headSideWasher"] == 1
    assert result.metrics["componentCounts"]["nutSideWasher"] == 0


def test_missing_nut_and_head_side_washer_reports_exact_side():
    instances = [
        _instance(1, "bolt", 50, 100),
        _instance(2, "washer", 220, 230, 10, 110),
        _instance(3, "thread", 240, 360, 35, 85),
    ]

    result = _evaluate(instances)

    assert result.metrics["assemblyReasons"] == [
        "NUT_MISSING",
        "WASHER_MISSING_HEAD_SIDE",
    ]
    assert result.metrics["componentCounts"]["headSideWasher"] == 0
    assert result.metrics["componentCounts"]["nutSideWasher"] == 1


def test_both_washers_missing_uses_generic_reason():
    instances = [
        _instance(1, "bolt", 50, 100),
        _instance(1, "bolt", 180, 220),
        _instance(3, "thread", 240, 360, 35, 85),
    ]

    result = _evaluate(instances)

    assert result.metrics["assemblyReasons"] == ["WASHER_MISSING"]


def test_missing_reference_geometry_uses_generic_washer_reason():
    instances = [
        _instance(2, "washer", 120, 130, 10, 110),
        _instance(3, "thread", 240, 360, 35, 85),
    ]

    result = _evaluate(instances)

    assert result.metrics["assemblyReasons"] == ["NUT_MISSING", "WASHER_MISSING"]
    assert result.metrics["componentCounts"]["headSideWasher"] is None
    assert result.metrics["componentCounts"]["nutSideWasher"] is None


def test_overlapping_head_thread_geometry_uses_generic_washer_reason():
    instances = [
        _instance(1, "bolt", 50, 250),
        _instance(2, "washer", 200, 210, 10, 110),
        _instance(3, "thread", 240, 360, 35, 85),
    ]

    result = _evaluate(instances)

    assert result.metrics["assemblyReasons"] == ["NUT_MISSING", "WASHER_MISSING"]
    assert result.metrics["componentCounts"]["unassignedWasher"] == 1


def test_lower_washer_missing_is_identified_as_nut_side_missing():
    instances = [
        item
        for index, item in enumerate(_normal_instances())
        if index != 2
    ]
    result = _evaluate(instances)

    assert result.component_result == DEFECT
    assert "WASHER_MISSING_NUT_SIDE" in result.metrics["failureReasons"]
    assert result.metrics["componentCounts"]["upperWasher"] == 1
    assert result.metrics["componentCounts"]["lowerWasher"] == 0


def test_upper_washer_missing_is_identified_as_head_side_missing():
    instances = [
        item
        for index, item in enumerate(_normal_instances())
        if index != 1
    ]
    result = _evaluate(instances)

    assert result.component_result == DEFECT
    assert "WASHER_MISSING_HEAD_SIDE" in result.metrics["failureReasons"]
    assert result.metrics["componentCounts"]["upperWasher"] == 0
    assert result.metrics["componentCounts"]["lowerWasher"] == 1


def test_short_thread_exposure_is_fastening_defect():
    result = _evaluate(_normal_instances(thread_end=290))

    assert result.component_result == NORMAL
    assert result.assembly_sequence_result == NORMAL
    assert result.fastening_quality_result == DEFECT
    assert result.metrics["threadExposureRatio"] < 1.36
    assert result.metrics["failureReasons"] == ["LOOSE"]


def test_unseated_nut_is_fastening_defect_even_when_order_is_valid():
    instances = _normal_instances()
    instances[3] = _instance(1, "bolt", 370, 410)
    result = _evaluate(instances)

    assert result.component_result == NORMAL
    assert result.assembly_sequence_result == NORMAL
    assert result.fastening_quality_result == DEFECT
    assert result.metrics["failureReasons"] == ["NUT_NOT_SEATED"]


def test_thread_missing_keeps_unavailable_measurements_as_none():
    result = _evaluate(
        [item for item in _normal_instances() if item.class_name != "thread"]
    )

    assert result.overall_result == DEFECT
    assert result.component_result == DEFECT
    assert result.assembly_sequence_result == NOT_EVALUATED
    assert result.fastening_quality_result == NOT_EVALUATED
    assert result.metrics["threadExposureRatio"] is None
    assert result.metrics["nutWasherGapPx"] is None
    assert result.metrics["nutTiltDeg"] is None
    assert result.metrics["failureReasons"] == ["THREAD_MISSING"]
    assert result.metrics["componentCounts"]["bolt"] is None
    assert result.metrics["componentCounts"]["nut"] is None
    assert result.metrics["componentCounts"]["upperWasher"] is None
    assert result.metrics["componentCounts"]["lowerWasher"] is None


def test_multiple_thread_components_use_largest_without_extra_defect():
    instances = _normal_instances()
    instances.append(_instance(3, "thread", 400, 410, 35, 45))
    result = _evaluate(instances)

    assert result.overall_result == NORMAL
    assert result.metrics["detectedCounts"]["thread"] == 2
    assert result.metrics["failureReasons"] == []


def test_configured_gap_limit_can_mark_fastening_defect():
    result = _evaluate(_normal_instances(), gap_ratio_max=0.01)

    assert result.fastening_quality_result == DEFECT
    assert "GAP" in result.metrics["failureReasons"]


def test_empty_instance_geometry_is_treated_as_missing_not_an_exception():
    empty_mask = np.zeros((460, 140), dtype=bool)
    empty_washer = DetectedInstance(
        class_id=2,
        class_name="washer",
        confidence=0.8,
        bbox=(0, 0, 0, 0),
        mask=empty_mask,
        contour=None,
        center=(0.0, 0.0),
        area_px=0,
    )
    instances = _normal_instances()
    instances[1] = empty_washer

    result = _evaluate(instances)

    assert result.component_result == DEFECT
    assert "WASHER_MISSING_HEAD_SIDE" in result.metrics["failureReasons"]
