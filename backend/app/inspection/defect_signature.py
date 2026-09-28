from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from typing import Any

from app.vision.contracts import InspectionResult


@dataclass(frozen=True, slots=True)
class DefectSignature:
    """Stable defect identity built from categorical and normalized geometry features."""

    overall_result: str
    missing_component_result: str
    alignment_result: str
    fastening_result: str
    detected_counts: tuple[tuple[str, int], ...]
    assembly_reasons: tuple[str, ...]
    geometry: tuple[tuple[str, float], ...]

    @classmethod
    def from_result(cls, result: InspectionResult) -> "DefectSignature":
        metrics = result.metrics or {}
        detections = _canonical_detections(metrics.get("detections"))
        counts = _detected_counts(metrics.get("detectedCounts"), detections)
        reasons = tuple(sorted({str(reason) for reason in metrics.get("assemblyReasons", [])}))
        return cls(
            overall_result=result.overall_result,
            missing_component_result=result.missing_component_result,
            alignment_result=result.alignment_result,
            fastening_result=result.fastening_result,
            detected_counts=counts,
            assembly_reasons=reasons,
            geometry=_geometry_features(result, detections),
        )

    def is_similar_to(self, other: "DefectSignature", tolerance_ratio: float) -> bool:
        if self._categorical_identity() != other._categorical_identity():
            return False
        if tuple(key for key, _ in self.geometry) != tuple(key for key, _ in other.geometry):
            return False
        tolerance = max(0.0, tolerance_ratio)
        return all(
            _within_tolerance(key, left, right, tolerance)
            for (key, left), (_, right) in zip(self.geometry, other.geometry)
        )

    def _categorical_identity(self) -> tuple[Any, ...]:
        return (
            self.overall_result,
            self.missing_component_result,
            self.alignment_result,
            self.fastening_result,
            self.detected_counts,
            self.assembly_reasons,
        )


def _detected_counts(raw_counts: Any, detections: list[dict[str, Any]]) -> tuple[tuple[str, int], ...]:
    if isinstance(raw_counts, dict):
        return tuple(sorted((str(name), int(count)) for name, count in raw_counts.items()))
    counts = Counter(str(item["class_name"]) for item in detections)
    return tuple(sorted(counts.items()))


def _canonical_detections(raw_detections: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_detections, list):
        return []
    parsed: list[dict[str, Any]] = []
    for raw in raw_detections:
        if not isinstance(raw, dict):
            continue
        bbox = raw.get("bbox")
        center = raw.get("center")
        if not _numeric_sequence(bbox, 4) or not _numeric_sequence(center, 2):
            continue
        x1, y1, x2, y2 = (float(value) for value in bbox)
        center_x, center_y = (float(value) for value in center)
        parsed.append(
            {
                "class_name": str(raw.get("className", "unknown")),
                "center_x": center_x,
                "center_y": center_y,
                "width": max(0.0, x2 - x1),
                "height": max(0.0, y2 - y1),
                "area": max(0.0, float(raw.get("areaPx", 0.0))),
                "x2": x2,
                "y2": y2,
            }
        )
    return sorted(
        parsed,
        key=lambda item: (
            item["class_name"],
            item["center_y"],
            item["center_x"],
            item["height"],
            item["width"],
        ),
    )


def _geometry_features(
    result: InspectionResult,
    detections: list[dict[str, Any]],
) -> tuple[tuple[str, float], ...]:
    if not detections:
        return ()
    frame_width, frame_height = _frame_size(result, detections)
    frame_area = frame_width * frame_height
    frame_diagonal = math.hypot(frame_width, frame_height)
    features: list[tuple[str, float]] = []
    labelled: list[tuple[str, dict[str, Any]]] = []
    ordinals: Counter[str] = Counter()

    for item in detections:
        class_name = item["class_name"]
        ordinal = ordinals[class_name]
        ordinals[class_name] += 1
        label = f"{class_name}:{ordinal}"
        labelled.append((label, item))
        features.extend(
            (
                (f"{label}.width", item["width"] / frame_width),
                (f"{label}.height", item["height"] / frame_height),
                (f"{label}.area", item["area"] / frame_area),
            )
        )

    if len(labelled) == 1:
        label, item = labelled[0]
        features.extend(
            (
                (f"{label}.center_x", item["center_x"] / frame_width),
                (f"{label}.center_y", item["center_y"] / frame_height),
            )
        )
    else:
        for (left_label, left), (right_label, right) in combinations(labelled, 2):
            dx = abs(left["center_x"] - right["center_x"])
            dy = abs(left["center_y"] - right["center_y"])
            pair = f"{left_label}|{right_label}"
            features.extend(
                (
                    (f"{pair}.dx", dx / frame_width),
                    (f"{pair}.dy", dy / frame_height),
                    (f"{pair}.distance", math.hypot(dx, dy) / frame_diagonal),
                )
            )

    measured = _finite_float((result.metrics or {}).get("measuredThreadCm"))
    threshold = _finite_float((result.metrics or {}).get("threadThresholdCm"))
    if measured is not None and threshold is not None and threshold > 0:
        features.append(("fastening.thread_ratio", measured / threshold))
    return tuple(features)


def _frame_size(
    result: InspectionResult,
    detections: list[dict[str, Any]],
) -> tuple[float, float]:
    if result.processed_frame is not None and result.processed_frame.ndim >= 2:
        height, width = result.processed_frame.shape[:2]
        return max(1.0, float(width)), max(1.0, float(height))
    if result.vision_result is not None:
        for instance in result.vision_result.instances:
            if instance.mask.ndim >= 2:
                height, width = instance.mask.shape[:2]
                return max(1.0, float(width)), max(1.0, float(height))
    return (
        max(1.0, max(item["x2"] for item in detections)),
        max(1.0, max(item["y2"] for item in detections)),
    )


def _numeric_sequence(value: Any, length: int) -> bool:
    if not isinstance(value, (list, tuple)) or len(value) != length:
        return False
    return all(_finite_float(item) is not None for item in value)


def _finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _within_tolerance(key: str, left: float, right: float, tolerance: float) -> bool:
    position_feature = key.endswith(
        (".center_x", ".center_y", ".dx", ".dy", ".distance")
    )
    if position_feature:
        return abs(left - right) <= tolerance
    scale = max(abs(left), abs(right), 1e-9)
    return abs(left - right) / scale <= tolerance
