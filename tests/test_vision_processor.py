import numpy as np

from backend.app.vision.mask_rcnn import MockVisionProcessor


def test_mock_processor_returns_overlay_without_mutating_raw_frame():
    processor = MockVisionProcessor()
    raw = np.zeros((120, 240, 3), dtype=np.uint8)

    result = processor.process(raw)

    assert result.processed_frame.shape == raw.shape
    assert np.count_nonzero(result.processed_frame) > 0
    assert np.count_nonzero(raw) == 0
    assert result.overall_result in {"NORMAL", "DEFECT"}
