from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math

import cv2
import numpy as np

from .contracts import (
    DEFECT,
    NORMAL,
    NOT_EVALUATED,
    DetectedInstance,
    FrameVisionResult,
    InspectionResult,
)


@dataclass(slots=True)
class _Part:
    instance: DetectedInstance
    points: np.ndarray
    t0: float = 0.0
    t1: float = 0.0
    role: str | None = None

    @property
    def center_t(self) -> float:
        return (self.t0 + self.t1) / 2.0


class InspectionDecisionEngine:
    """Apply the original U-NET/measure/judge.py geometry to detected instances."""

    def __init__(
        self,
        *,
        thread_ratio_min: float,
        expected_washer_count: int = 2,
        gap_ratio_max: float | None = None,
        bolt_diameter_mm: float | None = None,
    ) -> None:
        if expected_washer_count < 0:
            raise ValueError("expected_washer_count must be non-negative")
        if thread_ratio_min <= 0:
            raise ValueError("thread_ratio_min must be positive")
        if gap_ratio_max is not None and gap_ratio_max < 0:
            raise ValueError("gap_ratio_max must be non-negative")
        if bolt_diameter_mm is not None and bolt_diameter_mm <= 0:
            raise ValueError("bolt_diameter_mm must be positive")
        self.expected_washer_count = expected_washer_count
        self.thread_ratio_min = thread_ratio_min
        self.gap_ratio_max = gap_ratio_max
        self.bolt_diameter_mm = bolt_diameter_mm

    def evaluate(
        self, vision: FrameVisionResult, *, model_type: str
    ) -> InspectionResult:
        parts: list[_Part] = []
        for instance in vision.instances:
            part = self._part(instance)
            if len(part.points):
                parts.append(part)
        bolts = [part for part in parts if part.instance.class_name == "bolt"]
        washers = [part for part in parts if part.instance.class_name == "washer"]
        threads = [part for part in parts if part.instance.class_name == "thread"]
        reasons: list[dict[str, str]] = []
        component_result = NORMAL
        order_result = NORMAL
        fastening_result = NORMAL
        measurements: dict[str, float | None] = {
            "threadWidthPx": None,
            "threadExposureRatio": None,
            "threadExposureThreshold": self.thread_ratio_min,
            "nutWasherGapRatio": None,
            "nutWasherGapPx": None,
            "nutTiltDeg": None,
            "threadExposedMm": None,
            "nutWasherGapMm": None,
        }

        def fail(category: str, code: str, label: str) -> None:
            nonlocal component_result, order_result, fastening_result
            if category == "components":
                component_result = DEFECT
            elif category == "order":
                order_result = DEFECT
            else:
                fastening_result = DEFECT
            reasons.append({"category": category, "code": code, "label": label})

        thread: _Part | None = None
        nut: _Part | None = None
        head: _Part | None = None
        roles_evaluated = False
        if not threads:
            fail("components", "THREAD_MISSING", "나사산 미검출")
            order_result = NOT_EVALUATED
            fastening_result = NOT_EVALUATED
        else:
            thread = max(threads, key=lambda part: len(part.points))
            axis, perpendicular = self._estimate_axis(parts, thread)
            if axis is None or perpendicular is None:
                fail("components", "AXIS_FAIL", "볼트 축 추정 실패")
                order_result = NOT_EVALUATED
                fastening_result = NOT_EVALUATED
            else:
                for part in parts:
                    part.t0, part.t1 = self._span(part.points, axis)
                projected_width = thread.points @ perpendicular
                diameter = float(
                    np.percentile(projected_width, 98)
                    - np.percentile(projected_width, 2)
                )
                measurements["threadWidthPx"] = diameter if diameter > 0 else None
                nut, head = self._assign_roles(bolts, washers, thread)
                roles_evaluated = True
                self._check_components(bolts, washers, nut, fail)
                if component_result == NORMAL:
                    self._check_order(bolts, washers, fail)
                else:
                    order_result = NOT_EVALUATED
                if nut is not None and diameter > 0:
                    measurements.update(
                        self._measure_fastening(
                            thread, nut, washers, diameter, perpendicular
                        )
                    )
                    ratio = measurements["threadExposureRatio"]
                    if isinstance(ratio, float) and ratio < self.thread_ratio_min:
                        fail(
                            "fastening",
                            "LOOSE",
                            "체결 불량 (나사산 노출 부족)",
                        )
                    gap_ratio = measurements["nutWasherGapRatio"]
                    if (
                        self.gap_ratio_max is not None
                        and isinstance(gap_ratio, float)
                        and gap_ratio > self.gap_ratio_max
                    ):
                        fail("fastening", "GAP", "체결 불량 (너트-와셔 틈)")
                elif any(part.role == "unseated_nut" for part in bolts):
                    fail(
                        "fastening",
                        "NUT_NOT_SEATED",
                        "체결 불량 (너트 미체결: 나사산 끝에 걸림)",
                    )
                else:
                    fail(
                        "fastening",
                        "FASTEN_UNMEASURED",
                        "체결 상태 판정 불가 (체결된 너트 없음)",
                    )

        raw_counts = Counter(item.class_name for item in vision.instances)
        component_counts = self._component_counts(
            bolts, washers, threads, nut, head, roles_evaluated
        )
        reason_codes = [reason["code"] for reason in reasons]
        metrics: dict[str, object] = {
            "modelType": model_type,
            "detectedInstanceCount": len(vision.instances),
            "inferenceTimeMs": round(vision.inference_time_ms, 2),
            "detectedCounts": dict(sorted(raw_counts.items())),
            "detections": [
                self._serialize_detection(item) for item in vision.instances
            ],
            "componentResult": component_result,
            "assemblySequenceResult": order_result,
            "fasteningResult": fastening_result,
            "componentCounts": component_counts,
            "failureReasons": reason_codes,
            "failureReasonDetails": reasons,
            "assemblyReasons": [
                reason["code"]
                for reason in reasons
                if reason["category"] in {"components", "order"}
            ],
            "fasteningEvaluated": fastening_result != NOT_EVALUATED,
            **measurements,
        }
        overall = (
            NORMAL
            if component_result == order_result == fastening_result == NORMAL
            and not reasons
            else DEFECT
        )
        return InspectionResult(
            overall_result=overall,
            missing_component_result=component_result,
            alignment_result=order_result,
            fastening_result=fastening_result,
            metrics=metrics,
            inspection_time=vision.timestamp,
            vision_result=vision,
        )

    @staticmethod
    def _part(instance: DetectedInstance) -> _Part:
        if instance.geometry_points is not None:
            points = np.asarray(instance.geometry_points, dtype=np.float32)
        else:
            ys, xs = np.nonzero(instance.mask)
            points = np.column_stack((xs, ys)).astype(np.float32)
        return _Part(instance, points)

    @staticmethod
    def _span(
        points: np.ndarray, axis: np.ndarray, low: float = 1, high: float = 99
    ) -> tuple[float, float]:
        projected = points @ axis
        return (
            float(np.percentile(projected, low)),
            float(np.percentile(projected, high)),
        )

    @staticmethod
    def _estimate_axis(
        parts: list[_Part], thread: _Part
    ) -> tuple[np.ndarray | None, np.ndarray | None]:
        non_empty = [part.points for part in parts if len(part.points)]
        if not non_empty or not len(thread.points):
            return None, None
        all_points = np.concatenate(non_empty)
        vector = thread.points.mean(0) - all_points.mean(0)
        norm = np.linalg.norm(vector)
        if norm < 1e-3:
            return None, None
        axis = vector / norm
        return axis, np.array([-axis[1], axis[0]])

    @staticmethod
    def _assign_roles(
        bolts: list[_Part], washers: list[_Part], thread: _Part
    ) -> tuple[_Part | None, _Part | None]:
        thread_start = thread.t0
        below = sorted(
            [part for part in bolts if part.center_t < thread_start],
            key=lambda part: -part.t1,
        )
        nut = below[0] if len(below) >= 2 else None
        head = below[-1] if below else None
        beyond_role = "extra_nut" if nut is not None else "unseated_nut"
        for part in bolts:
            part.role = (
                "nut"
                if part is nut
                else "head"
                if part is head
                else beyond_role
            )
        if nut is not None and head is not None:
            midpoint = (nut.t0 + head.t1) / 2.0
            for washer in washers:
                washer.role = (
                    "nut_side_washer"
                    if washer.center_t > midpoint
                    else "head_side_washer"
                )
        elif head is not None:
            anchor_values = (head.t0, head.t1, thread.t0, thread.t1)
            anchor_span = thread.t0 - head.t1
            if all(math.isfinite(value) for value in anchor_values) and anchor_span > 1e-9:
                for washer in washers:
                    washer_values = (washer.t0, washer.t1, washer.center_t)
                    if not all(math.isfinite(value) for value in washer_values):
                        continue
                    if not head.t1 <= washer.center_t <= thread.t0:
                        continue
                    distance_to_head = max(0.0, washer.t0 - head.t1)
                    distance_to_thread = max(0.0, thread.t0 - washer.t1)
                    if distance_to_head < distance_to_thread:
                        washer.role = "head_side_washer"
                    elif distance_to_thread < distance_to_head:
                        washer.role = "nut_side_washer"
        return nut, head

    def _check_components(
        self,
        bolts: list[_Part],
        washers: list[_Part],
        nut: _Part | None,
        fail,
    ) -> None:
        if len(bolts) < 2:
            fail("components", "NUT_MISSING", "너트 누락")
        elif len(bolts) > 2:
            fail("components", "NUT_EXTRA", "너트 과다")
        if len(washers) < self.expected_washer_count:
            roles = {washer.role for washer in washers}
            if len(washers) == 1 and "nut_side_washer" in roles:
                fail(
                    "components",
                    "WASHER_MISSING_HEAD_SIDE",
                    "볼트머리측 와셔 누락",
                )
            elif len(washers) == 1 and "head_side_washer" in roles:
                fail(
                    "components",
                    "WASHER_MISSING_NUT_SIDE",
                    "너트측 와셔 누락",
                )
            else:
                fail(
                    "components",
                    "WASHER_MISSING",
                    f"와셔 누락 ({self.expected_washer_count - len(washers)}개)",
                )
        elif len(washers) > self.expected_washer_count:
            fail("components", "WASHER_EXTRA", "와셔 과다")

    @staticmethod
    def _check_order(
        bolts: list[_Part], washers: list[_Part], fail
    ) -> None:
        sequence = [
            part.instance.class_name
            for part in sorted(
                bolts + washers, key=lambda part: -part.center_t
            )
        ]
        if sequence != ["bolt", "washer", "washer", "bolt"]:
            fail("order", "ORDER_ERROR", "조립 순서 이상")

    def _measure_fastening(
        self,
        thread: _Part,
        nut: _Part,
        washers: list[_Part],
        diameter: float,
        perpendicular: np.ndarray,
    ) -> dict[str, float | None]:
        ratio = (thread.t1 - thread.t0) / diameter
        result: dict[str, float | None] = {
            "threadExposureRatio": float(ratio),
        }
        nut_side = [
            washer
            for washer in washers
            if washer.role == "nut_side_washer"
        ]
        if nut_side:
            washer = max(nut_side, key=lambda part: part.t1)
            gap_px = nut.t0 - washer.t1
            result["nutWasherGapPx"] = float(gap_px)
            result["nutWasherGapRatio"] = float(gap_px / diameter)
        (_, _), (width, height), angle = cv2.minAreaRect(nut.points)
        long_angle = np.deg2rad(angle if width >= height else angle + 90)
        direction = np.array([np.cos(long_angle), np.sin(long_angle)])
        result["nutTiltDeg"] = float(
            np.degrees(
                np.arccos(min(1.0, abs(float(direction @ perpendicular))))
            )
        )
        if self.bolt_diameter_mm is not None:
            result["threadExposedMm"] = float(
                ratio * self.bolt_diameter_mm
            )
            gap_ratio = result.get("nutWasherGapRatio")
            if isinstance(gap_ratio, float):
                result["nutWasherGapMm"] = float(
                    gap_ratio * self.bolt_diameter_mm
                )
        return result

    @staticmethod
    def _component_counts(
        bolts: list[_Part],
        washers: list[_Part],
        threads: list[_Part],
        nut: _Part | None,
        head: _Part | None,
        roles_evaluated: bool,
    ) -> dict[str, int | None]:
        if not roles_evaluated:
            return {
                "bolt": None,
                "nut": None,
                "upperWasher": None,
                "lowerWasher": None,
                "nutSideWasher": None,
                "headSideWasher": None,
                "thread": int(bool(threads)),
            }
        washer_roles = {"head_side_washer", "nut_side_washer"}
        washer_roles_available = head is not None and all(
            part.role in washer_roles for part in washers
        )
        return {
            "bolt": int(head is not None),
            "nut": int(
                nut is not None
                or any(part.role == "unseated_nut" for part in bolts)
            ),
            "upperWasher": (
                sum(part.role == "head_side_washer" for part in washers)
                if washer_roles_available
                else None
            ),
            "lowerWasher": (
                sum(part.role == "nut_side_washer" for part in washers)
                if washer_roles_available
                else None
            ),
            "nutSideWasher": (
                sum(part.role == "nut_side_washer" for part in washers)
                if washer_roles_available
                else None
            ),
            "headSideWasher": (
                sum(part.role == "head_side_washer" for part in washers)
                if washer_roles_available
                else None
            ),
            "unassignedWasher": sum(part.role not in washer_roles for part in washers),
            "thread": int(bool(threads)),
        }

    @staticmethod
    def _serialize_detection(
        instance: DetectedInstance,
    ) -> dict[str, object]:
        return {
            "classId": instance.class_id,
            "className": instance.class_name,
            "confidence": round(instance.confidence, 4),
            "bbox": list(instance.bbox),
            "center": [
                round(instance.center[0], 2),
                round(instance.center[1], 2),
            ],
            "areaPx": instance.area_px,
        }
