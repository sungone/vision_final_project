from __future__ import annotations

import logging
import queue
import threading
import time
from collections.abc import Callable

from app.vision.contracts import InspectionResult


logger = logging.getLogger(__name__)


class InspectionPersistenceWorker:
    """Persists confirmed events without blocking inference or the MJPEG path."""

    def __init__(
        self,
        persist: Callable[[InspectionResult], None],
        *,
        queue_size: int = 100,
        retry_seconds: float = 2.0,
    ) -> None:
        self.persist = persist
        self.retry_seconds = max(0.1, retry_seconds)
        self._queue: queue.Queue[InspectionResult] = queue.Queue(maxsize=max(1, queue_size))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.running = False
        self.last_error: str | None = None
        self.persisted_count = 0

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="inspection-persistence",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 3.0) -> None:
        deadline = time.monotonic() + max(0.0, timeout)
        while self._queue.unfinished_tasks and time.monotonic() < deadline:
            time.sleep(0.02)
        self._stop.set()
        if self._thread and self._thread.is_alive() and threading.current_thread() is not self._thread:
            self._thread.join(max(0.0, deadline - time.monotonic()))

    def submit(self, result: InspectionResult) -> None:
        try:
            self._queue.put_nowait(result)
        except queue.Full as exc:
            raise RuntimeError("inspection persistence queue is full") from exc

    @property
    def pending_count(self) -> int:
        return self._queue.qsize()

    def _run(self) -> None:
        self.running = True
        try:
            while not self._stop.is_set():
                try:
                    result = self._queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                try:
                    self._persist_with_retry(result)
                finally:
                    self._queue.task_done()
        finally:
            self.running = False

    def _persist_with_retry(self, result: InspectionResult) -> None:
        while not self._stop.is_set():
            try:
                self.persist(result)
                self.last_error = None
                self.persisted_count += 1
                return
            except Exception as exc:
                self.last_error = str(exc)
                logger.exception("inspection event persistence failed; retrying")
                if self._stop.wait(self.retry_seconds):
                    return
