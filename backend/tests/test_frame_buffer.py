import numpy as np

from app.camera import LatestFrameBuffer


def test_latest_frame_replaces_old_and_is_copied():
    buffer = LatestFrameBuffer()
    original = np.zeros((2, 2, 3), dtype=np.uint8)
    buffer.put(original)
    original[:] = 9
    first = buffer.get()
    assert first is not None
    assert int(first.value.max()) == 0
    buffer.put(np.full((2, 2, 3), 7, dtype=np.uint8))
    latest = buffer.get(after_version=first.version, timeout=0)
    assert latest is not None
    assert int(latest.value.min()) == 7

