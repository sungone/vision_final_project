import time

import cv2
import numpy as np

from app.camera import CameraCaptureWorker, LatestFrameBuffer


class FakeCapture:
    def __init__(self, source) -> None:
        self.source = source
        self.released = False
        self.settings = []

    def set(self, prop, value):
        self.settings.append((prop, value))
        return True

    def isOpened(self):
        return not self.released

    def read(self):
        time.sleep(0.005)
        return True, np.full((12, 16, 3), 7, dtype=np.uint8)

    def release(self):
        self.released = True


def test_camera_worker_opens_once_publishes_latest_frame_and_releases():
    created = []

    def factory(source):
        capture = FakeCapture(source)
        created.append(capture)
        return capture

    frames = LatestFrameBuffer()
    worker = CameraCaptureWorker(
        frames,
        camera_index="2",
        width=1280,
        height=720,
        fps=30,
        reconnect_seconds=0.01,
        capture_factory=factory,
    )
    worker.start()
    try:
        snapshot = frames.get(after_version=0, timeout=2.0)
        assert snapshot is not None
        assert int(snapshot.value[0, 0, 0]) == 7
        assert len(created) == 1
        assert created[0].source == 2
        settings = dict(created[0].settings)
        assert settings[cv2.CAP_PROP_BUFFERSIZE] == 1
        assert settings[cv2.CAP_PROP_FOURCC] == cv2.VideoWriter_fourcc(*"MJPG")
        assert settings[cv2.CAP_PROP_FRAME_WIDTH] == 1280
        assert settings[cv2.CAP_PROP_FRAME_HEIGHT] == 720
        assert settings[cv2.CAP_PROP_FPS] == 30
        assert worker.connected is True
    finally:
        worker.stop()

    assert created[0].released is True
    assert worker.running is False
    assert worker.connected is False
