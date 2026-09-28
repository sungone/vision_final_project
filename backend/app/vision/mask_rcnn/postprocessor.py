from __future__ import annotations

from datetime import datetime, timezone

import cv2
import numpy as np
import torch

from ..contracts import DetectedInstance, FrameVisionResult


class SegmentationPostProcessor:
    def __init__(self, label_to_name: dict[int, str], score_threshold: float, mask_threshold: float) -> None:
        self.label_to_name = label_to_name
        self.score_threshold = score_threshold
        self.mask_threshold = mask_threshold

    def process(self, prediction: dict[str, torch.Tensor], inference_time_ms: float) -> FrameVisionResult:
        required = {"boxes", "labels", "scores", "masks"}
        if not required.issubset(prediction):
            raise ValueError(f"prediction is missing keys: {sorted(required.difference(prediction))}")
        scores_device = prediction["scores"].detach()
        valid_indices = torch.nonzero(scores_device >= self.score_threshold, as_tuple=False).flatten()
        boxes = prediction["boxes"].detach()[valid_indices].cpu()
        labels = prediction["labels"].detach()[valid_indices].cpu()
        scores = scores_device[valid_indices].cpu()
        masks = prediction["masks"].detach()[valid_indices].cpu()
        if masks.ndim != 4 or masks.shape[1] != 1:
            raise ValueError(f"unexpected mask shape: {tuple(masks.shape)}")

        instances: list[DetectedInstance] = []
        for box, label_tensor, score_tensor, mask_tensor in zip(boxes, labels, scores, masks):
            score = float(score_tensor.item())
            class_id = int(label_tensor.item())
            class_name = self.label_to_name.get(class_id)
            if class_name is None:
                continue
            binary_mask = mask_tensor[0].numpy() >= self.mask_threshold
            mask_uint8 = binary_mask.astype(np.uint8)
            contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            contour = max(contours, key=cv2.contourArea) if contours else None
            x1, y1, x2, y2 = (int(round(value)) for value in box.tolist())
            moments = cv2.moments(mask_uint8, binaryImage=True)
            center = (
                (moments["m10"] / moments["m00"], moments["m01"] / moments["m00"])
                if moments["m00"] else ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
            )
            instances.append(DetectedInstance(
                class_id=class_id, class_name=class_name, confidence=score,
                bbox=(x1, y1, x2, y2), mask=binary_mask, contour=contour,
                center=center, area_px=int(np.count_nonzero(binary_mask)),
            ))
        return FrameVisionResult(datetime.now(timezone.utc), instances, inference_time_ms)
