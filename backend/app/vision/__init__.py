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
from .decision_engine import InspectionDecisionEngine
from .mask_rcnn import MaskRCNNVisionProcessor, MockVisionProcessor
from .unet import UNetVisionProcessor
from .yolo26 import YOLO26VisionProcessor

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
    "InspectionDecisionEngine",
    "UNetVisionProcessor",
    "YOLO26VisionProcessor",
]
