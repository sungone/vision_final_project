from __future__ import annotations

import threading
import time
from enum import Enum

from app.vision.contracts import InspectionResult


class InspectionState(str, Enum):
    NORMAL = "NORMAL"
    DEFECT_CANDIDATE = "DEFECT_CANDIDATE"
    CONFIRMED_DEFECT = "CONFIRMED_DEFECT"


class InspectionEventManager:
    """Converts frame-level results into at-most-once defect events per defect episode."""

    def __init__(self, confirm_frames: int, reset_frames: int, cooldown_seconds: float = 0.0) -> None:
        self.confirm_frames = max(1, confirm_frames)
        self.reset_frames = max(1, reset_frames)
        self.cooldown_seconds = max(0.0, cooldown_seconds)
        self._lock = threading.Lock()
        self._state = InspectionState.NORMAL
        self._defect_count = 0
        self._normal_count = 0
        self._last_emitted_monotonic = float("-inf")

    def consume(self, result: InspectionResult) -> InspectionResult | None:
        with self._lock:
            if result.is_defect:
                self._normal_count = 0
                if self._state == InspectionState.CONFIRMED_DEFECT:
                    return None
                self._defect_count += 1
                self._state = InspectionState.DEFECT_CANDIDATE
                if self._defect_count < self.confirm_frames:
                    return None
                self._state = InspectionState.CONFIRMED_DEFECT
                self._defect_count = 0
                now = time.monotonic()
                if now - self._last_emitted_monotonic < self.cooldown_seconds:
                    self._state = InspectionState.DEFECT_CANDIDATE
                    self._defect_count = self.confirm_frames - 1
                    return None
                self._last_emitted_monotonic = now
                return result

            self._defect_count = 0
            if self._state == InspectionState.CONFIRMED_DEFECT:
                self._normal_count += 1
                if self._normal_count >= self.reset_frames:
                    self._state = InspectionState.NORMAL
                    self._normal_count = 0
            else:
                self._state = InspectionState.NORMAL
                self._normal_count = 0
            return None

    @property
    def state(self) -> InspectionState:
        with self._lock:
            return self._state


