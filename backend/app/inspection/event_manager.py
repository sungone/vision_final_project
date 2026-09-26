from __future__ import annotations

import threading
import time
from collections.abc import Callable
from enum import Enum

from app.vision.contracts import InspectionResult

from .defect_signature import DefectSignature


class InspectionState(str, Enum):
    NORMAL = "NORMAL"
    CONFIRMED_DEFECT = "CONFIRMED_DEFECT"


class InspectionEventManager:
    """Sample frame results and emit only meaningfully changed defect states."""

    def __init__(
        self,
        *,
        reset_frames: int,
        sample_fps: float = 1.0,
        geometry_tolerance_ratio: float = 0.05,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.reset_frames = max(1, reset_frames)
        self.sample_fps = max(0.001, sample_fps)
        self.geometry_tolerance_ratio = min(1.0, max(0.0, geometry_tolerance_ratio))
        self._sample_interval = 1.0 / self.sample_fps
        self._clock = clock
        self._lock = threading.Lock()
        self._state = InspectionState.NORMAL
        self._normal_count = 0
        self._next_sample_at = float("-inf")
        self._last_signature: DefectSignature | None = None
        self._signature_before_emit: DefectSignature | None = None
        self._emission_can_rollback = False

    def consume(self, result: InspectionResult) -> InspectionResult | None:
        with self._lock:
            now = self._clock()
            if now < self._next_sample_at:
                return None
            self._next_sample_at = now + self._sample_interval

            if not result.is_defect:
                self._consume_normal()
                return None

            self._normal_count = 0
            signature = DefectSignature.from_result(result)
            if self._last_signature is not None and signature.is_similar_to(
                self._last_signature,
                self.geometry_tolerance_ratio,
            ):
                self._state = InspectionState.CONFIRMED_DEFECT
                return None

            self._signature_before_emit = self._last_signature
            self._last_signature = signature
            self._emission_can_rollback = True
            self._state = InspectionState.CONFIRMED_DEFECT
            return result

    def _consume_normal(self) -> None:
        if self._last_signature is None:
            self._state = InspectionState.NORMAL
            self._normal_count = 0
            return
        self._normal_count += 1
        if self._normal_count >= self.reset_frames:
            self._last_signature = None
            self._signature_before_emit = None
            self._emission_can_rollback = False
            self._normal_count = 0
            self._state = InspectionState.NORMAL

    def mark_event_delivery_failed(self) -> None:
        """Roll back signature state when the event could not enter persistence."""
        with self._lock:
            if not self._emission_can_rollback:
                return
            self._last_signature = self._signature_before_emit
            self._signature_before_emit = None
            self._emission_can_rollback = False
            self._state = (
                InspectionState.CONFIRMED_DEFECT
                if self._last_signature is not None
                else InspectionState.NORMAL
            )

    @property
    def state(self) -> InspectionState:
        with self._lock:
            return self._state
