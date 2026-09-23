"""Public vision contracts without importing the worker eagerly.

``VisionWorker`` deliberately is not re-exported here: it depends on the
inspection event manager, while that manager depends on these contracts.
Import it from ``app.vision.worker`` where needed.
"""

from .contracts import DEFECT, NORMAL, NOT_EVALUATED, InspectionResult, VisionProcessor
from .processor import MockVisionProcessor

__all__ = [
    "DEFECT",
    "NORMAL",
    "NOT_EVALUATED",
    "InspectionResult",
    "VisionProcessor",
    "MockVisionProcessor",
]
