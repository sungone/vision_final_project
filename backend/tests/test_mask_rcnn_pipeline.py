from datetime import datetime, timezone

import numpy as np
import torch

from app.vision.contracts import DetectedInstance, FrameVisionResult
from app.vision.mask_rcnn import SegmentationPostProcessor
from app.vision.visualizer import InspectionVisualizer


def test_postprocessor_filters_scores_and_builds_structured_instances():
    masks = torch.zeros((2, 1, 20, 20), dtype=torch.float32)
    masks[0, 0, 4:12, 5:14] = 0.9
    masks[1, 0, 1:3, 1:3] = 0.9
    prediction = {
        "boxes": torch.tensor([[5, 4, 14, 12], [1, 1, 3, 3]], dtype=torch.float32),
        "labels": torch.tensor([1, 2]),
        "scores": torch.tensor([0.95, 0.25]),
        "masks": masks,
    }

    result = SegmentationPostProcessor({1: "bolt", 2: "washer"}, 0.7, 0.5).process(prediction, 12.3)

    assert len(result.instances) == 1
    assert result.instances[0].class_name == "bolt"
    assert result.instances[0].area_px == 72
    assert result.instances[0].contour is not None


def test_visualizer_uses_blue_for_bolt_and_yellow_for_washer():
    bolt_mask = np.zeros((30, 40), dtype=bool)
    bolt_mask[2:12, 2:12] = True
    washer_mask = np.zeros((30, 40), dtype=bool)
    washer_mask[16:26, 25:35] = True
    instances = [
        DetectedInstance(1, "bolt", 0.95, (2, 2, 12, 12), bolt_mask, None, (7, 7), 100),
        DetectedInstance(2, "washer", 0.94, (25, 16, 35, 26), washer_mask, None, (30, 21), 100),
    ]
    result = FrameVisionResult(datetime.now(timezone.utc), instances, 10.0)

    rendered = InspectionVisualizer(overlay_alpha=1.0, draw_boxes=False, draw_stats=False).render(
        np.zeros((30, 40, 3), dtype=np.uint8), result
    )

    assert tuple(rendered[7, 7]) == (255, 0, 0)
    assert tuple(rendered[21, 30]) == (0, 255, 255)


def test_stream_endpoint_declares_mjpeg_content_type(client):
    client.application.extensions["vision_runtime"].encoded_frames.put(b"\xff\xd8\xff\xd9")
    response = client.get("/api/v1/stream", buffered=False)
    assert response.status_code == 200
    assert response.content_type == "multipart/x-mixed-replace; boundary=frame"
    response.close()
