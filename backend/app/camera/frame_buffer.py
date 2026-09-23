from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Generic, TypeVar

import numpy as np


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class BufferSnapshot(Generic[T]):
    value: T
    version: int
    captured_at: datetime


class LatestValueBuffer(Generic[T]):
    """Keeps one latest value; slow consumers skip stale values instead of building backlog."""

    def __init__(self, copy_numpy: bool = False) -> None:
        self._condition = threading.Condition()
        self._value: T | None = None
        self._version = 0
        self._captured_at: datetime | None = None
        self._copy_numpy = copy_numpy

    def put(self, value: T, captured_at: datetime | None = None) -> int:
        stored = value.copy() if self._copy_numpy and isinstance(value, np.ndarray) else value
        with self._condition:
            self._value = stored
            self._version += 1
            self._captured_at = captured_at or datetime.now(timezone.utc)
            self._condition.notify_all()
            return self._version

    def get(self, after_version: int | None = None, timeout: float | None = None) -> BufferSnapshot[T] | None:
        with self._condition:
            if after_version is not None and self._version <= after_version:
                self._condition.wait_for(lambda: self._version > after_version, timeout=timeout)
            if self._value is None or (after_version is not None and self._version <= after_version):
                return None
            value = self._value.copy() if self._copy_numpy and isinstance(self._value, np.ndarray) else self._value
            return BufferSnapshot(value, self._version, self._captured_at or datetime.now(timezone.utc))

    @property
    def version(self) -> int:
        with self._condition:
            return self._version


class LatestFrameBuffer(LatestValueBuffer[np.ndarray]):
    def __init__(self) -> None:
        super().__init__(copy_numpy=True)

