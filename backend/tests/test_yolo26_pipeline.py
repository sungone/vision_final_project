from types import SimpleNamespace

import numpy as np
import torch

from app.vision.yolo26_postprocessor import YOLO26SegmentationPostProcessor


def test_yolo26_postprocessor_builds_structured_instances_and_resizes_masks():
    result = SimpleNamespace(
        boxes=SimpleNamespace(
            xyxy=torch.tensor([[4.0, 6.0, 20.0, 22.0]]),
            cls=torch.tensor([1.0]),
            conf=torch.tensor([0.91]),
            __len__=lambda self: 1,
        ),
        masks=SimpleNamespace(data=torch.ones((1, 16, 16), dtype=torch.float32)),
    )
    # SimpleNamespace does not provide special-method dispatch for __len__.
    result.boxes = _FakeBoxes(result.boxes.xyxy, result.boxes.cls, result.boxes.conf)

    processed = YOLO26SegmentationPostProcessor({0: "bolt", 1: "washer", 2: "thread"}).process(
        result, 8.2, (32, 40, 3)
    )

    assert len(processed.instances) == 1
    instance = processed.instances[0]
    assert instance.class_name == "washer"
    assert instance.bbox == (4, 6, 20, 22)
    assert instance.mask.shape == (32, 40)
    assert instance.area_px == 1280


def test_yolo26_postprocessor_accepts_empty_predictions():
    result = SimpleNamespace(boxes=_FakeBoxes.empty(), masks=None)
    processed = YOLO26SegmentationPostProcessor({0: "bolt"}).process(result, 3.1, (20, 20, 3))
    assert processed.instances == []


class _FakeBoxes:
    def __init__(self, xyxy, classes, confidence):
        self.xyxy = xyxy
        self.cls = classes
        self.conf = confidence

    def __len__(self):
        return len(self.xyxy)

    @classmethod
    def empty(cls):
        return cls(torch.empty((0, 4)), torch.empty(0), torch.empty(0))
