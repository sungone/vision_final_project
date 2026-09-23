from __future__ import annotations

import numpy as np

from .contracts import InspectionResult, NOT_EVALUATED
from .visualizer import InspectionVisualizer
from .yolo26_postprocessor import YOLO26SegmentationPostProcessor
from .yolo26_predictor import YOLO26SegPredictor


class YOLO26VisionProcessor:
    def __init__(
        self,
        predictor: YOLO26SegPredictor,
        postprocessor: YOLO26SegmentationPostProcessor,
        visualizer: InspectionVisualizer,
    ) -> None:
        self.predictor = predictor
        self.postprocessor = postprocessor
        self.visualizer = visualizer

    @property
    def device_name(self) -> str:
        return self.predictor.device_name

    def process(self, frame: np.ndarray) -> InspectionResult:
        prediction, inference_time_ms = self.predictor.predict(frame)
        vision_result = self.postprocessor.process(prediction, inference_time_ms, frame.shape)
        processed = self.visualizer.render(frame, vision_result)
        return InspectionResult(
            overall_result=NOT_EVALUATED,
            missing_component_result=NOT_EVALUATED,
            alignment_result=NOT_EVALUATED,
            fastening_result=NOT_EVALUATED,
            metrics={
                "modelType": "yolo26-seg",
                "detectedInstanceCount": len(vision_result.instances),
                "inferenceTimeMs": round(inference_time_ms, 2),
            },
            processed_frame=processed,
            inspection_time=vision_result.timestamp,
            vision_result=vision_result,
        )
