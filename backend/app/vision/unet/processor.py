from __future__ import annotations

import numpy as np

from ..contracts import InspectionResult
from ..decision_engine import InspectionDecisionEngine
from ..visualizer import InspectionVisualizer
from .postprocessor import UNetSegmentationPostProcessor
from .predictor import UNetSegPredictor


class UNetVisionProcessor:
    def __init__(
        self,
        predictor: UNetSegPredictor,
        postprocessor: UNetSegmentationPostProcessor,
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
        class_map, probabilities, inference_time_ms = self.predictor.predict(frame)
        vision_result = self.postprocessor.process(class_map, probabilities, inference_time_ms)
        inspection = self.decision_engine.evaluate(vision_result, model_type="u-net-resnet18")
        inspection.processed_frame = self.visualizer.render(frame, vision_result, inspection)
        return inspection
