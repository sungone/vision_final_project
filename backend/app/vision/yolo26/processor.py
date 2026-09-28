from __future__ import annotations

import numpy as np

from ..contracts import InspectionResult
from ..decision_engine import InspectionDecisionEngine
from ..visualizer import InspectionVisualizer
from .postprocessor import YOLO26SegmentationPostProcessor
from .predictor import YOLO26SegPredictor


class YOLO26VisionProcessor:
    def __init__(
        self,
        predictor: YOLO26SegPredictor,
        postprocessor: YOLO26SegmentationPostProcessor,
        decision_engine: InspectionDecisionEngine,
        visualizer: InspectionVisualizer,
    ) -> None:
        self.predictor = predictor
        self.postprocessor = postprocessor
        self.decision_engine = decision_engine
        self.visualizer = visualizer

    @property
    def device_name(self) -> str:
        return self.predictor.device_name

    def process(self, frame: np.ndarray) -> InspectionResult:
        prediction, inference_time_ms = self.predictor.predict(frame)
        vision_result = self.postprocessor.process(prediction, inference_time_ms, frame.shape)
        inspection = self.decision_engine.evaluate(vision_result, model_type="yolo26-seg")
        inspection.processed_frame = self.visualizer.render(frame, vision_result, inspection)
        return inspection
