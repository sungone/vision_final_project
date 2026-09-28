from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from .contracts import DEFECT, InspectionResult


SEPARATOR = "=" * 60
LOGGER_NAME = "app.vision.live_inspection"


def format_live_inspection(result: InspectionResult) -> str:
    """Format only values already stored on the live InspectionResult."""
    metrics = result.metrics or {}
    lines = [
        SEPARATOR,
        f"[Vision Inspection] {result.inspection_time.isoformat()}",
        SEPARATOR,
        "",
        "[Decision]",
        f"Overall              : {result.overall_result}",
        f"Component            : {result.missing_component_result}",
        f"Assembly Sequence    : {result.assembly_sequence_result}",
        f"Fastening Quality    : {result.fastening_quality_result}",
    ]

    reasons = _reasons(metrics)
    if result.overall_result == DEFECT:
        lines.extend(["", "Reasons:", *(f"- {reason}" for reason in reasons or ["N/A"])])

    lines.extend(
        [
            "",
            "[Measurement]",
            f"Thread Exposure Ratio: {_number(_get(metrics, 'threadExposureRatio'), 3)}",
            f"Threshold            : {_number(_get(metrics, 'threadExposureThreshold'), 3)}",
            f"Nut-Washer Gap       : {_number(_get(metrics, 'nutWasherGapPx', 'nutWasherGap'), 2, ' px')}",
            f"Nut Tilt             : {_number(_get(metrics, 'nutTiltDeg', 'nutTilt'), 2, ' deg')}",
            "",
            "[Vision]",
            f"Model                 : {_text(_get(metrics, 'modelType', 'modelName'))}",
            f"Instances             : {_text(_get(metrics, 'detectedInstanceCount'))}",
            f"Detected Counts       : {_counts(_get(metrics, 'detectedCounts'))}",
            "",
            "[Performance]",
            f"Vision FPS            : {_number(_get(metrics, 'visionFps'), 2)}",
            f"Inference             : {_number(_get(metrics, 'inferenceTimeMs'), 2, ' ms')}",
            f"Processing            : {_number(_get(metrics, 'processingTimeMs'), 2, ' ms')}",
            "",
            "[Detections]",
        ]
    )

    detections = _get(metrics, "detections")
    if isinstance(detections, list) and detections:
        formatted = [_format_detection(item) for item in detections if isinstance(item, Mapping)]
        lines.extend(formatted or ["N/A"])
    else:
        lines.append("N/A")
    lines.extend(["", SEPARATOR])
    return "\n".join(lines)


class LiveInspectionLogger:
    def __init__(
        self,
        enabled: bool,
        interval_seconds: float,
        *,
        target_logger: logging.Logger | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.enabled = enabled
        self.interval_seconds = max(0.0, interval_seconds)
        self._logger = target_logger or _console_logger(enabled)
        self._clock = clock
        self._last_logged_at: float | None = None

    def maybe_log(self, result: InspectionResult) -> bool:
        if not self.enabled:
            return False
        now = self._clock()
        if self._last_logged_at is not None and now - self._last_logged_at < self.interval_seconds:
            return False
        self._last_logged_at = now
        self._logger.info("\n%s", format_live_inspection(result))
        return True


def _get(metrics: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in metrics and metrics[key] is not None:
            return metrics[key]
    return None


def _console_logger(enabled: bool) -> logging.Logger:
    target = logging.getLogger(LOGGER_NAME)
    if enabled:
        if not target.handlers:
            target.addHandler(logging.StreamHandler())
        target.setLevel(logging.INFO)
        target.propagate = False
    return target


def _text(value: Any) -> str:
    return "N/A" if value is None else str(value)


def _number(value: Any, precision: int, suffix: str = "") -> str:
    if value is None or isinstance(value, bool):
        return "N/A"
    try:
        return f"{float(value):.{precision}f}{suffix}"
    except (TypeError, ValueError):
        return "N/A"


def _counts(value: Any) -> str:
    if not isinstance(value, Mapping) or not value:
        return "N/A"
    return ", ".join(f"{name}={count}" for name, count in sorted(value.items()))


def _reasons(metrics: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("reasons", "assemblyReasons", "fasteningReasons"):
        reasons = metrics.get(key)
        if isinstance(reasons, str):
            reasons = [reasons]
        if isinstance(reasons, Iterable) and not isinstance(reasons, (str, bytes, Mapping)):
            for reason in reasons:
                text = str(reason)
                if text and text not in values:
                    values.append(text)
    return values


def _format_detection(detection: Mapping[str, Any]) -> str:
    name = _text(detection.get("className", detection.get("class")))
    confidence = _number(detection.get("confidence"), 3)
    bbox = _compact_sequence(detection.get("bbox"))
    center = _compact_sequence(detection.get("center"))
    area = _text(detection.get("areaPx"))
    return f"{name:<7} conf={confidence} bbox={bbox} center={center} areaPx={area}"


def _compact_sequence(value: Any) -> str:
    if not isinstance(value, (list, tuple)):
        return "N/A"
    return "[" + ",".join(str(item) for item in value) + "]"
