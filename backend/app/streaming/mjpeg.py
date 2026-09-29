from __future__ import annotations

import time

from app.camera.frame_buffer import LatestValueBuffer


BOUNDARY = b"frame"


def generate_mjpeg(encoded_frames: LatestValueBuffer[bytes], fps: float):
    interval = 1.0 / max(0.1, fps)
    last_version = 0
    while True:
        snapshot = encoded_frames.get(after_version=last_version, timeout=2.0)
        if snapshot is None:
            continue
        last_version = snapshot.version
        payload = snapshot.value
        yield (
            b"--" + BOUNDARY + b"\r\n"
            b"Content-Type: image/jpeg\r\n"
            b"Content-Length: " + str(len(payload)).encode("ascii") + b"\r\n\r\n"
            + payload + b"\r\n"
        )
        time.sleep(interval)

