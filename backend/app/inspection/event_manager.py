from __future__ import annotations

import threading
import time
from collections.abc import Callable
from enum import Enum

from app.vision.contracts import InspectionResult


class InspectionState(str, Enum):
    NORMAL = "NORMAL"
    CONFIRMED_DEFECT = "CONFIRMED_DEFECT"


class InspectionEventManager:
    """Emit the latest inspection result at a fixed sampling interval."""

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
        self._next_sample_at = float("-inf")

    def consume(self, result: InspectionResult) -> InspectionResult | None:
        with self._lock:
            now = self._clock()
            if now < self._next_sample_at:
                return None
            self._next_sample_at = now + self._sample_interval
            self._state = (
                InspectionState.CONFIRMED_DEFECT
                if result.is_defect
                else InspectionState.NORMAL
            )
            return result

    def mark_event_delivery_failed(self) -> None:
        """Keep the fixed sampling schedule after a queue delivery failure."""

    @property
    def state(self) -> InspectionState:
        with self._lock:
            return self._state
