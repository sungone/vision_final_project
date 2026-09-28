from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import math

import cv2
import numpy as np

from .contracts import DEFECT, NORMAL, NOT_EVALUATED, DetectedInstance, FrameVisionResult, InspectionResult


@dataclass(slots=True)
class ProjectedInstance:
    instance: DetectedInstance
    t0: float
    t1: float
    center_t: float
    pixels_xy: np.ndarray


@dataclass(slots=True)
class AssignedRoles:
    head: ProjectedInstance | None = None
    nut: ProjectedInstance | None = None
    unseated_nuts: list[ProjectedInstance] = field(default_factory=list)
    extra_nuts: list[ProjectedInstance] = field(default_factory=list)
    nut_side_washers: list[ProjectedInstance] = field(default_factory=list)
    head_side_washers: list[ProjectedInstance] = field(default_factory=list)


@dataclass(slots=True)
class RuleDecision:
    result: str
    reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class FasteningDecision(RuleDecision):
    thread_ratio: float | None = None
    exposed_thread_px: float | None = None
    gap_ratio: float | None = None
    gap_px: float | None = None
    nut_tilt_deg: float | None = None
    diameter_px: float | None = None


class InspectionDecisionEngine:
    """Apply the mask-geometry rules used by the offline judge to live detections."""

    EXPECTED_ORDER = ("BOLT", "WASHER", "WASHER", "BOLT")

    def __init__(
        self,
        *,
        expected_washer_count: int = 2,
        thread_exposure_min_ratio: float = 1.36,
        gap_ratio_max: float | None = None,
        bolt_diameter_mm: float | None = None,
    ) -> None:
        if expected_washer_count != 2:
            raise ValueError("judge rules require expected_washer_count=2")
        if not math.isfinite(thread_exposure_min_ratio) or thread_exposure_min_ratio <= 0:
            raise ValueError("thread_exposure_min_ratio must be positive")
        if gap_ratio_max is not None and (not math.isfinite(gap_ratio_max) or gap_ratio_max < 0):
            raise ValueError("gap_ratio_max must be non-negative")
        if bolt_diameter_mm is not None and (
            not math.isfinite(bolt_diameter_mm) or bolt_diameter_mm <= 0
        ):
            raise ValueError("bolt_diameter_mm must be positive")
        self.expected_washer_count = expected_washer_count
        self.thread_exposure_min_ratio = thread_exposure_min_ratio
        self.gap_ratio_max = gap_ratio_max
        self.bolt_diameter_mm = bolt_diameter_mm

    def evaluate(self, vision: FrameVisionResult, *, model_type: str) -> InspectionResult:
        metrics = self._base_metrics(vision, model_type)
        thread_instances = [item for item in vision.instances if item.class_name.lower() == "thread"]
        if not thread_instances:
            reasons = ["THREAD_MISSING"]
            metrics.update(
                {
                    "componentReasons": reasons,
                    "assemblyReasons": reasons,
                    "fasteningReasons": [],
                    "reasons": reasons,
                    "fasteningEvaluated": False,
                    "threadExposureThreshold": self.thread_exposure_min_ratio,
                    "gapRatioMax": self.gap_ratio_max,
                }
            )
            return InspectionResult(
                overall_result=DEFECT,
                missing_component_result=DEFECT,
                alignment_result=NOT_EVALUATED,
                fastening_result=NOT_EVALUATED,
                metrics=metrics,
                inspection_time=vision.timestamp,
                vision_result=vision,
            )

        thread_instance = max(thread_instances, key=self._pixel_count)
        axis, perpendicular = self._axis_vectors(vision.instances, thread_instance)
        projected = [self._project(item, axis) for item in vision.instances]
        thread = next(item for item in projected if item.instance is thread_instance)
        diameter_px = self._percentile_width(thread.pixels_xy @ perpendicular, 2.0, 98.0)
        roles = self.assign_roles(projected, thread)

        component = self.check_components(projected, roles)
        sequence = (
            self.check_sequence(projected)
            if component.result == NORMAL
            else RuleDecision(NOT_EVALUATED)
        )
        fastening = self.check_fastening(thread, roles, perpendicular, diameter_px)
        reasons = component.reasons + sequence.reasons + fastening.reasons
        overall = (
            NORMAL
            if component.result == NORMAL
            and sequence.result == NORMAL
            and fastening.result == NORMAL
            and not reasons
            else DEFECT
        )

        metrics.update(
            {
                "componentReasons": component.reasons,
                "assemblyReasons": component.reasons + sequence.reasons,
                "fasteningReasons": fastening.reasons,
                "reasons": reasons,
                "fasteningEvaluated": fastening.thread_ratio is not None,
                "threadExposureThreshold": self.thread_exposure_min_ratio,
                "gapRatioMax": self.gap_ratio_max,
                "boltDiameterPx": self._rounded(diameter_px, 3),
            }
        )
        self._add_fastening_metrics(metrics, fastening)
        return InspectionResult(
            overall_result=overall,
            missing_component_result=component.result,
            alignment_result=sequence.result,
            fastening_result=fastening.result,
            metrics=metrics,
            inspection_time=vision.timestamp,
            vision_result=vision,
        )

    def assign_roles(
        self, projected: list[ProjectedInstance], thread: ProjectedInstance
    ) -> AssignedRoles:
        bolts = [item for item in projected if item.instance.class_name.lower() == "bolt"]
        washers = [item for item in projected if item.instance.class_name.lower() == "washer"]
        below = sorted(
            (item for item in bolts if item.center_t < thread.t0), key=lambda item: item.center_t
        )
        outside = sorted(
            (item for item in bolts if item.center_t >= thread.t0), key=lambda item: item.center_t
        )
        roles = AssignedRoles()
        if len(below) >= 2:
            roles.head = below[0]
            roles.nut = below[-1]
            roles.extra_nuts = below[1:-1] + outside
        elif len(below) == 1:
            roles.head = below[0]
            roles.unseated_nuts = outside
        else:
            roles.unseated_nuts = outside

        if roles.head is not None and roles.nut is not None:
            midpoint = (roles.head.center_t + roles.nut.center_t) / 2.0
            roles.nut_side_washers = [item for item in washers if item.center_t >= midpoint]
            roles.head_side_washers = [item for item in washers if item.center_t < midpoint]
        return roles

    def check_components(
        self, projected: list[ProjectedInstance], roles: AssignedRoles
    ) -> RuleDecision:
        bolts = [item for item in projected if item.instance.class_name.lower() == "bolt"]
        washers = [item for item in projected if item.instance.class_name.lower() == "washer"]
        reasons: list[str] = []
        if len(bolts) < 2:
            reasons.append("NUT_MISSING")
        elif len(bolts) >= 3:
            reasons.append("NUT_EXTRA")

        if len(washers) == 1 and roles.nut is not None:
            if roles.nut_side_washers:
                reasons.append("WASHER_MISSING_HEAD_SIDE")
            else:
                reasons.append("WASHER_MISSING_NUT_SIDE")
        elif len(washers) < self.expected_washer_count:
            reasons.append("WASHER_MISSING")
        elif len(washers) > self.expected_washer_count:
            reasons.append("WASHER_EXTRA")
        return RuleDecision(NORMAL if not reasons else DEFECT, reasons)

    def check_sequence(self, projected: list[ProjectedInstance]) -> RuleDecision:
        parts = [
            item
            for item in projected
            if item.instance.class_name.lower() in {"bolt", "washer"}
        ]
        actual = tuple(item.instance.class_name.upper() for item in sorted(parts, key=lambda x: x.center_t, reverse=True))
        reasons = [] if actual == self.EXPECTED_ORDER else ["ORDER_INVALID"]
        return RuleDecision(NORMAL if not reasons else DEFECT, reasons)

    def check_fastening(
        self,
        thread: ProjectedInstance,
        roles: AssignedRoles,
        perpendicular: np.ndarray,
        diameter_px: float | None,
    ) -> FasteningDecision:
        if roles.nut is None:
            reason = "NUT_NOT_SEATED" if roles.unseated_nuts else "FASTEN_UNMEASURED"
            return FasteningDecision(DEFECT, [reason], diameter_px=diameter_px)
        if diameter_px is None or diameter_px <= 0:
            return FasteningDecision(
                DEFECT, ["FASTEN_UNMEASURED"], diameter_px=diameter_px
            )

        exposed_thread_px = max(0.0, thread.t1 - thread.t0)
        thread_ratio = exposed_thread_px / diameter_px
        nut_side_washer = (
            max(roles.nut_side_washers, key=lambda item: item.center_t)
            if roles.nut_side_washers
            else None
        )
        gap_px = roles.nut.t0 - nut_side_washer.t1 if nut_side_washer is not None else None
        gap_ratio = gap_px / diameter_px if gap_px is not None else None
        nut_tilt_deg = self._nut_tilt(roles.nut.pixels_xy, perpendicular)
        reasons: list[str] = []
        if (
            thread_ratio
            < self.thread_exposure_min_ratio
            and not math.isclose(
                thread_ratio,
                self.thread_exposure_min_ratio,
                rel_tol=1e-9,
                abs_tol=1e-9,
            )
        ):
            reasons.append("LOOSE")

        if (
            self.gap_ratio_max is not None
            and gap_ratio is not None
            and gap_ratio > self.gap_ratio_max
            and not math.isclose(
                gap_ratio,
                self.gap_ratio_max,
                rel_tol=1e-9,
                abs_tol=1e-9,
            )
        ):
            reasons.append("GAP")

        return FasteningDecision(
            NORMAL if not reasons else DEFECT,
            reasons,
            thread_ratio=thread_ratio,
            exposed_thread_px=exposed_thread_px,
            gap_ratio=gap_ratio,
            gap_px=gap_px,
            nut_tilt_deg=nut_tilt_deg,
            diameter_px=diameter_px,
        )

    def _add_fastening_metrics(
        self,
        metrics: dict[str, object],
        fastening: FasteningDecision,
    ) -> None:
        displayed_thread_ratio = self._rounded(
            fastening.thread_ratio,
            3,
        )
        displayed_gap_ratio = self._rounded(
            fastening.gap_ratio,
            3,
        )

        values = {
            "threadExposureRatio": displayed_thread_ratio,
            "threadExposurePx": self._rounded(
                fastening.exposed_thread_px,
                2,
            ),
            "nutWasherGapRatio": displayed_gap_ratio,
            "nutWasherGapPx": self._rounded(
                fastening.gap_px,
                2,
            ),
            "nutTiltDeg": self._rounded(
                fastening.nut_tilt_deg,
                2,
            ),
        }

        metrics.update(
            {
                key: value
                for key, value in values.items()
                if value is not None
            }
        )

        if self.bolt_diameter_mm is not None:
            if displayed_thread_ratio is not None:
                metrics["threadExposureMm"] = round(
                    displayed_thread_ratio
                    * self.bolt_diameter_mm,
                    3,
                )

            if displayed_gap_ratio is not None:
                metrics["nutWasherGapMm"] = round(
                    displayed_gap_ratio
                    * self.bolt_diameter_mm,
                    3,
                )

    def _base_metrics(self, vision: FrameVisionResult, model_type: str) -> dict[str, object]:
        counts = Counter(item.class_name for item in vision.instances)
        return {
            "modelType": model_type,
            "detectedInstanceCount": len(vision.instances),
            "inferenceTimeMs": round(vision.inference_time_ms, 2),
            "detectedCounts": dict(sorted(counts.items())),
            "detections": [self._serialize_detection(item) for item in vision.instances],
            "threadExposureRatio": None,
            "threadExposurePx": None,
            "nutWasherGapRatio": None,
            "nutWasherGapPx": None,
            "nutTiltDeg": None,
        }

    @classmethod
    def _axis_vectors(
        cls, instances: list[DetectedInstance], thread: DetectedInstance
    ) -> tuple[np.ndarray, np.ndarray]:
        all_pixels = np.concatenate([cls._pixels_xy(item) for item in instances], axis=0)
        all_center = np.mean(all_pixels, axis=0)
        thread_center = np.mean(cls._pixels_xy(thread), axis=0)
        axis = thread_center - all_center
        norm = float(np.linalg.norm(axis))
        if norm <= 1e-9:
            axis = np.array([0.0, 1.0], dtype=np.float64)
        else:
            axis = axis / norm
        return axis, np.array([-axis[1], axis[0]], dtype=np.float64)

    @classmethod
    def _project(cls, instance: DetectedInstance, axis: np.ndarray) -> ProjectedInstance:
        pixels_xy = cls._pixels_xy(instance)
        values = pixels_xy @ axis
        t0, t1 = np.percentile(values, [1.0, 99.0])
        center_t = float(np.asarray(instance.center, dtype=np.float64) @ axis)
        return ProjectedInstance(instance, float(t0), float(t1), center_t, pixels_xy)

    @staticmethod
    def _pixels_xy(instance: DetectedInstance) -> np.ndarray:
        rows, columns = np.nonzero(instance.mask)
        if rows.size:
            return np.column_stack((columns, rows)).astype(np.float64)
        return np.asarray([instance.center], dtype=np.float64)

    @staticmethod
    def _percentile_width(values: np.ndarray, low: float, high: float) -> float | None:
        if values.size < 2:
            return None
        start, end = np.percentile(values, [low, high])
        width = float(end - start)
        return width if width > 0 else None

    @staticmethod
    def _nut_tilt(pixels_xy: np.ndarray, perpendicular: np.ndarray) -> float | None:
        if len(pixels_xy) < 3:
            return None
        rectangle = cv2.minAreaRect(pixels_xy.astype(np.float32))
        box = cv2.boxPoints(rectangle).astype(np.float64)
        edges = np.roll(box, -1, axis=0) - box
        lengths = np.linalg.norm(edges, axis=1)
        long_edge = edges[int(np.argmax(lengths))]
        length = float(np.linalg.norm(long_edge))
        if length <= 1e-9:
            return None
        cosine = float(np.clip(abs(np.dot(long_edge / length, perpendicular)), 0.0, 1.0))
        return float(np.degrees(np.arccos(cosine)))

    @staticmethod
    def _pixel_count(instance: DetectedInstance) -> int:
        return int(np.count_nonzero(instance.mask)) or instance.area_px

    @staticmethod
    def _rounded(value: float | None, precision: int) -> float | None:
        return None if value is None else round(float(value), precision)

    @staticmethod
    def _serialize_detection(instance: DetectedInstance) -> dict[str, object]:
        return {
            "classId": instance.class_id,
            "className": instance.class_name,
            "confidence": round(instance.confidence, 4),
            "bbox": list(instance.bbox),
            "center": [round(instance.center[0], 2), round(instance.center[1], 2)],
            "areaPx": instance.area_px,
        }
