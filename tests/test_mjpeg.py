import numpy as np

from backend.app.camera.frame_buffer import LatestFrameBuffer
from backend.app.streaming.mjpeg import generate_mjpeg


def test_mjpeg_chunk_has_boundary_headers_and_jpeg_payload():
    buffer = LatestFrameBuffer()
    buffer.update(np.zeros((32, 32, 3), dtype=np.uint8))

    chunk = next(generate_mjpeg(buffer, fps=30, jpeg_quality=75))

    assert chunk.startswith(b"--frame\r\n")
    assert b"Content-Type: image/jpeg\r\n" in chunk
    assert b"\r\n\r\n\xff\xd8" in chunk
    assert chunk.endswith(b"\r\n")
