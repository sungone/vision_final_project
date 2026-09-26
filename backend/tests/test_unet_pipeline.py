import numpy as np
import torch

from app.vision.contracts import DEFECT, NORMAL
from app.vision.decision_engine import InspectionDecisionEngine
from app.vision.unet import ResNet18UNet, UNetSegmentationPostProcessor


def test_unet_architecture_outputs_full_resolution_logits():
    model = ResNet18UNet(class_count=4).eval()

    with torch.inference_mode():
        result = model(torch.zeros((1, 3, 64, 64)))

    assert result.shape == (1, 4, 64, 64)


def test_unet_postprocessor_splits_semantic_classes_into_instances():
    class_map = np.zeros((420, 80), dtype=np.uint8)
    class_map[0:90, 20:60] = 1
    class_map[90:114, 20:60] = 2
    class_map[116:140, 20:60] = 2
    class_map[140:230, 20:60] = 1
    class_map[230:410, 20:60] = 3
    probabilities = np.full((4, 420, 80), 0.02, dtype=np.float32)
    for class_id in range(4):
        probabilities[class_id][class_map == class_id] = 0.94

    vision = UNetSegmentationPostProcessor(
        {0: "background", 1: "bolt", 2: "washer", 3: "thread"},
        min_component_area=20,
    ).process(class_map, probabilities, 8.5)
    result = InspectionDecisionEngine().evaluate(vision, model_type="u-net-test")

    assert [item.class_name for item in vision.instances] == [
        "bolt",
        "washer",
        "washer",
        "bolt",
        "thread",
    ]
    assert result.assembly_sequence_result == NORMAL
    assert result.fastening_quality_result == DEFECT
    assert result.metrics["threadThresholdCm"] == 2.16
    assert result.metrics["detectedInstanceCount"] == 5
