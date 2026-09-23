from __future__ import annotations

from datetime import datetime, timezone

import cv2
import numpy as np

from .contracts import InspectionResult, NORMAL, NOT_EVALUATED
from .mask_rcnn_predictor import MaskRCNNPredictor
from .postprocessor import SegmentationPostProcessor
from .visualizer import InspectionVisualizer


class MaskRCNNVisionProcessor:
    def __init__(
        self,
        predictor: MaskRCNNPredictor,
        postprocessor: SegmentationPostProcessor,
        visualizer: InspectionVisualizer,
    ) -> None:
        self.predictor = predictor
        self.postprocessor = postprocessor
        self.visualizer = visualizer

    @property
    def device_name(self) -> str:
        return str(self.predictor.device)

    def process(self, frame: np.ndarray) -> InspectionResult:
        prediction, inference_time_ms = self.predictor.predict(frame)
        vision_result = self.postprocessor.process(prediction, inference_time_ms)
        processed = self.visualizer.render(frame, vision_result)
        return InspectionResult(
            overall_result=NOT_EVALUATED,
            missing_component_result=NOT_EVALUATED,
            alignment_result=NOT_EVALUATED,
            fastening_result=NOT_EVALUATED,
            metrics={
                "detectedInstanceCount": len(vision_result.instances),
                "inferenceTimeMs": round(inference_time_ms, 2),
            },
            processed_frame=processed,
            inspection_time=vision_result.timestamp,
            vision_result=vision_result,
        )


class MockVisionProcessor:
    """Replace this class with the future YOLO + rule engine adapter."""

    def process(self, frame: np.ndarray) -> InspectionResult:
        processed = frame.copy()
        now = datetime.now(timezone.utc)
        height, width = processed.shape[:2]
        cv2.rectangle(processed, (8, 8), (max(220, width // 3), 78), (0, 0, 0), -1)
        cv2.putText(processed, "VISION MOCK - NORMAL", (20, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 220, 0), 2)
        cv2.putText(processed, now.isoformat(timespec="seconds"), (20, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (230, 230, 230), 1)
        cv2.rectangle(processed, (2, 2), (width - 3, height - 3), (0, 180, 0), 3)
        return InspectionResult(
            overall_result=NORMAL,
            missing_component_result=NORMAL,
            alignment_result=NORMAL,
            fastening_result=NORMAL,
            metrics={},
            processed_frame=processed,
            inspection_time=now,
        )
