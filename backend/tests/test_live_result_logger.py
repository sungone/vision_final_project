from datetime import datetime, timezone
import logging

from app.vision import DEFECT, InspectionResult
from app.vision.live_result_logger import LiveInspectionLogger, format_live_inspection


def _result() -> InspectionResult:
    return InspectionResult(
        overall_result=DEFECT,
        missing_component_result=DEFECT,
        alignment_result="NOT_EVALUATED",
        fastening_result="NOT_EVALUATED",
        inspection_time=datetime(2026, 9, 28, 1, 22, 34, 512000, tzinfo=timezone.utc),
        metrics={
            "threadExposureRatio": 1.42,
            "threadExposureThreshold": 1.36,
            "nutWasherGapPx": 4.8,
            "nutTiltDeg": 2.7,
            "modelType": "u-net-resnet18",
            "detectedInstanceCount": 2,
            "detectedCounts": {"washer": 1, "bolt": 1},
            "assemblyRoleCounts": {
                "boltHead": 1,
                "nut": 0,
                "headSideWasher": 1,
                "nutSideWasher": 0,
                "unassignedWasher": 0,
                "thread": 1,
            },
            "visionFps": 9.84,
            "inferenceTimeMs": 82.31,
            "processingTimeMs": 96.44,
            "assemblyReasons": ["washer_count_1", "no_thread"],
            "detections": [
                {
                    "className": "bolt",
                    "confidence": 0.982,
                    "bbox": [421, 180, 512, 602],
                    "center": [466.5, 391.0],
                    "areaPx": 18342,
                }
            ],
        },
    )


def test_formats_only_values_from_inspection_result():
    output = format_live_inspection(_result())

    assert "Overall              : DEFECT" in output
    assert "Thread Exposure Ratio: 1.420" in output
    assert "Threshold            : 1.360" in output
    assert "Vision FPS            : 9.84" in output
    assert "Bolt Head             : 1" in output
    assert "Nut                   : 0" in output
    assert "Head-side Washer      : 1" in output
    assert "Nut-side Washer       : 0" in output
    assert "- washer_count_1" in output
    assert "bolt    conf=0.982 bbox=[421,180,512,602]" in output
    assert "areaPx=18342" in output


def test_missing_measurements_are_not_rendered_as_zero():
    result = InspectionResult(overall_result=DEFECT, metrics={"detections": []})

    output = format_live_inspection(result)

    assert "Thread Exposure Ratio: N/A" in output
    assert "Threshold            : N/A" in output
    assert "Nut-Washer Gap       : N/A" in output
    assert "Nut Tilt             : N/A" in output
    assert "Reasons:\n- N/A" in output
    assert "[Detections]\nN/A" in output


def test_live_logger_respects_enabled_flag_and_interval(caplog):
    ticks = iter((10.0, 10.4, 11.0))
    target = logging.getLogger("test.live.inspection")
    live_logger = LiveInspectionLogger(True, 1.0, target_logger=target, clock=lambda: next(ticks))
    disabled = LiveInspectionLogger(False, 1.0, target_logger=target)

    with caplog.at_level(logging.INFO, logger=target.name):
        assert live_logger.maybe_log(_result()) is True
        assert live_logger.maybe_log(_result()) is False
        assert live_logger.maybe_log(_result()) is True
        assert disabled.maybe_log(_result()) is False

    assert caplog.text.count("[Vision Inspection]") == 2
