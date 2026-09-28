from __future__ import annotations

import threading

from app.camera.frame_buffer import LatestValueBuffer

from .contracts import InspectionResult
from .live_result_logger import LiveInspectionLogger


class LiveInspectionConsole:
    """Print the latest inspection result at a bounded refresh rate."""

    def __init__(
        self,
        latest_results: LatestValueBuffer[InspectionResult],
        refresh_fps: float,
    ) -> None:
        self.latest_results = latest_results
        self.refresh_fps = max(0.1, float(refresh_fps))
        self._logger = LiveInspectionLogger(True, 0.0)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="live-inspection-console",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 3.0) -> None:
        self._stop.set()
        if (
            self._thread
            and self._thread.is_alive()
            and threading.current_thread() is not self._thread
        ):
            self._thread.join(timeout)

    def _run(self) -> None:
        last_version = 0
        interval = 1.0 / self.refresh_fps
        while not self._stop.is_set():
            snapshot = self.latest_results.get(
                after_version=last_version,
                timeout=interval,
            )
            if snapshot is None:
                continue
            last_version = snapshot.version
            self._logger.maybe_log(snapshot.value)
            self._stop.wait(interval)
