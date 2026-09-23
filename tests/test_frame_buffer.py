import threading

import numpy as np

from backend.app.camera.frame_buffer import LatestFrameBuffer


def test_latest_frame_replaces_older_frame_and_returns_a_copy():
    buffer = LatestFrameBuffer()
    first = np.zeros((4, 4, 3), dtype=np.uint8)
    latest = np.full((4, 4, 3), 17, dtype=np.uint8)

    buffer.update(first)
    buffer.update(latest)

    received = buffer.get()
    assert np.array_equal(received, latest)

    received[0, 0, 0] = 255
    assert buffer.get()[0, 0, 0] == 17


def test_concurrent_reads_and_writes_do_not_expose_partial_frames():
    buffer = LatestFrameBuffer()
    buffer.update(np.zeros((12, 12, 3), dtype=np.uint8))
    failures: list[str] = []

    def writer() -> None:
        for value in range(1, 80):
            buffer.update(np.full((12, 12, 3), value, dtype=np.uint8))

    def reader() -> None:
        for _ in range(300):
            frame = buffer.get()
            if frame is None or not np.all(frame == frame[0, 0, 0]):
                failures.append("partial frame observed")

    threads = [threading.Thread(target=writer)] + [
        threading.Thread(target=reader) for _ in range(4)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert failures == []
