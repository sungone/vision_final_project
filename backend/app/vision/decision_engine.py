from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

import numpy as np

from .contracts import DEFECT, NORMAL, NOT_EVALUATED, DetectedInstance, FrameVisionResult, InspectionResult


@dataclass(slots=True)
class AssemblyDecision:
    result: str
    reasons: list[str] = field(default_factory=list)
    head: DetectedInstance | None = None
    nut: DetectedInstance | None = None
    washers: list[DetectedInstance] = field(default_factory=list)
    thread: DetectedInstance | None = None


@dataclass(slots=True)
class FasteningDecision:
    result: str
    measured_thread_cm: float | None = None
    scale_cm_per_px: float | None = None
    threshold_cm: float | None = None


class InspectionDecisionEngine:
    """Convert model-independent segmentation instances into inspection results."""

    def __init__(self, *, expected_washer_count: int = 2, reference_head_cm: float = 1.0,
                 reference_nut_cm: float = 1.0, reference_washer_cm: float = 0.3,
                 full_thread_cm: float = 2.0, tightness_min_ratio: float = 1.08) -> None:
        if expected_washer_count < 0:
            raise ValueError("expected_washer_count must be non-negative")
        if (
            reference_head_cm <= 0
            or reference_nut_cm <= 0
            or reference_washer_cm <= 0
            or full_thread_cm <= 0
            or tightness_min_ratio <= 0
        ):
            raise ValueError("decision measurement settings must be positive")
        self.expected_washer_count = expected_washer_count
        self.reference_head_cm = reference_head_cm
        self.reference_nut_cm = reference_nut_cm
        self.reference_washer_cm = reference_washer_cm
        self.full_thread_cm = full_thread_cm
        self.tightness_min_ratio = tightness_min_ratio

    def evaluate(self, vision: FrameVisionResult, *, model_type: str) -> InspectionResult:
        assembly = self.check_assembly(vision.instances)
        fastening = self.check_fastening(assembly) if assembly.result == NORMAL else FasteningDecision(NOT_EVALUATED)
        overall = NORMAL if assembly.result == NORMAL and fastening.result == NORMAL else DEFECT
        counts = Counter(item.class_name for item in vision.instances)
        metrics: dict[str, object] = {
            "modelType": model_type,
            "detectedInstanceCount": len(vision.instances),
            "inferenceTimeMs": round(vision.inference_time_ms, 2),
            "detectedCounts": dict(sorted(counts.items())),
            "detections": [self._serialize_detection(item) for item in vision.instances],
            "assemblyReasons": assembly.reasons,
            "fasteningEvaluated": fastening.result != NOT_EVALUATED,
        }
        if fastening.measured_thread_cm is not None:
            metrics.update({
                "measuredThreadCm": round(fastening.measured_thread_cm, 3),
                "threadThresholdCm": round(fastening.threshold_cm or 0.0, 3),
                "scaleCmPerPx": round(fastening.scale_cm_per_px or 0.0, 6),
            })
        return InspectionResult(
            overall_result=overall,
            missing_component_result=assembly.result,
            alignment_result=NOT_EVALUATED,
            fastening_result=fastening.result,
            metrics=metrics,
            inspection_time=vision.timestamp,
            vision_result=vision,
        )

    def check_assembly(self, instances: list[DetectedInstance]) -> AssemblyDecision:
        threads = [item for item in instances if item.class_name == "thread"]
        bolts = [item for item in instances if item.class_name == "bolt"]
        washers = [item for item in instances if item.class_name == "washer"]
        reasons: list[str] = []
        thread = threads[0] if len(threads) == 1 else None
        head: DetectedInstance | None = None
        nut: DetectedInstance | None = None
        if len(threads) == 0:
            reasons.append("no_thread")
        elif len(threads) > 1:
            reasons.append(f"dup_thread({len(threads)})")
        if len(bolts) == 0:
            reasons.append("no_bolt")
        elif len(bolts) == 1:
            head = bolts[0]
            reasons.append("no_nut")
        else:
            if thread is not None:
                ordered = sorted(bolts, key=lambda item: abs(self._center_y(item) - self._center_y(thread)))
                nut, head = ordered[0], ordered[-1]
            if len(bolts) > 2:
                reasons.append(f"extra_bolt({len(bolts)})")
        washer_count = len(washers)
        if washer_count < self.expected_washer_count:
            reasons.append(f"washer_low({washer_count})")
        elif washer_count > self.expected_washer_count:
            reasons.append(f"washer_high({washer_count})")
        return AssemblyDecision(NORMAL if not reasons else DEFECT, reasons, head, nut, washers, thread)

    def check_fastening(self, assembly: AssemblyDecision) -> FasteningDecision:
        if assembly.result != NORMAL or assembly.head is None or assembly.nut is None or assembly.thread is None:
            return FasteningDecision(NOT_EVALUATED)
        reference_px = (self._axis_length(assembly.head) + self._axis_length(assembly.nut)) / 2.0
        if reference_px <= 0:
            raise ValueError("bolt reference length must be greater than zero")
        scale = self.reference_head_cm / reference_px
        measured = self._axis_length(assembly.thread) * scale
        threshold = self.full_thread_cm * self.tightness_min_ratio
        return FasteningDecision(
            NORMAL if measured >= threshold else DEFECT,
            measured_thread_cm=measured,
            scale_cm_per_px=scale,
            threshold_cm=threshold,
        )

    @staticmethod
    def _axis_extent(instance: DetectedInstance) -> tuple[float, float]:
        rows = np.flatnonzero(np.any(instance.mask, axis=1))
        if rows.size:
            return float(rows[0]), float(rows[-1] + 1)
        return float(instance.bbox[1]), float(instance.bbox[3])

    @classmethod
    def _axis_length(cls, instance: DetectedInstance) -> float:
        start, end = cls._axis_extent(instance)
        return end - start

    @classmethod
    def _center_y(cls, instance: DetectedInstance) -> float:
        start, end = cls._axis_extent(instance)
        return (start + end) / 2.0

    @staticmethod
    def _serialize_detection(instance: DetectedInstance) -> dict[str, object]:
        """Keep searchable detection metadata without persisting masks or contours."""
        return {
            "classId": instance.class_id,
            "className": instance.class_name,
            "confidence": round(instance.confidence, 4),
            "bbox": list(instance.bbox),
            "center": [round(instance.center[0], 2), round(instance.center[1], 2)],
            "areaPx": instance.area_px,
        }
