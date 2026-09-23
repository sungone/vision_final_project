from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Callable

import cv2

from .frame_buffer import LatestFrameBuffer


class CameraCaptureWorker:
    def __init__(
        self,
        frame_buffer: LatestFrameBuffer,
        camera_index: str,
        width: int,
        height: int,
        fps: float,
        reconnect_seconds: float = 2.0,
        capture_factory: Callable = cv2.VideoCapture,
    ) -> None:
        self.frame_buffer = frame_buffer
        self.camera_index = _camera_source(camera_index)
        self.width = width
        self.height = height
        self.fps = fps
        self.reconnect_seconds = reconnect_seconds
        self.capture_factory = capture_factory
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._capture = None
        self.connected = False
        self.running = False
        self.last_frame_at: datetime | None = None
        self.last_error: str | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="camera-capture", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 3.0) -> None:
        self._stop.set()
        capture = self._capture
        if capture is not None:
            capture.release()
        if self._thread and self._thread.is_alive() and threading.current_thread() is not self._thread:
            self._thread.join(timeout)

    def _run(self) -> None:
        self.running = True
        try:
            while not self._stop.is_set():
                capture = None
                try:
                    capture = self.capture_factory(self.camera_index)
                    self._capture = capture
                    capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    capture.set(cv2.CAP_PROP_FPS, self.fps)
                    if not capture.isOpened():
                        raise RuntimeError(f"camera {self.camera_index!r} could not be opened")
                    self.connected = True
                    self.last_error = None
                    while not self._stop.is_set():
                        ok, frame = capture.read()
                        if not ok or frame is None:
                            raise RuntimeError("camera frame read failed")
                        now = datetime.now(timezone.utc)
                        self.frame_buffer.put(frame, now)
                        self.last_frame_at = now
                except Exception as exc:  # camera backends expose heterogeneous exceptions
                    self.last_error = str(exc)
                    self.connected = False
                    if not self._stop.wait(self.reconnect_seconds):
                        continue
                finally:
                    if capture is not None:
                        capture.release()
                    self._capture = None
        finally:
            self.connected = False
            self.running = False


def _camera_source(value: str):
    stripped = str(value).strip()
    try:
        return int(stripped)
    except ValueError:
        return stripped

