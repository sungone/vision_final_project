"""Public vision contracts without importing the worker eagerly.

``VisionWorker`` deliberately is not re-exported here: it depends on the
inspection event manager, while that manager depends on these contracts.
Import it from ``app.vision.worker`` where needed.
"""

from .contracts import (
    DEFECT,
    NORMAL,
    NOT_EVALUATED,
    DetectedInstance,
    FrameVisionResult,
    InspectionResult,
    VisionProcessor,
)
from .mask_rcnn_processor import MaskRCNNVisionProcessor, MockVisionProcessor

__all__ = [
    "DEFECT",
    "NORMAL",
    "NOT_EVALUATED",
    "DetectedInstance",
    "FrameVisionResult",
    "InspectionResult",
    "VisionProcessor",
    "MaskRCNNVisionProcessor",
    "MockVisionProcessor",
]
