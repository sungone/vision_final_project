from __future__ import annotations

from datetime import datetime, timezone

import cv2
import numpy as np

from ..contracts import DetectedInstance, FrameVisionResult


class UNetSegmentationPostProcessor:
    def __init__(self, label_to_name: dict[int, str], min_component_area: int = 50) -> None:
        self.label_to_name = label_to_name
        self.min_component_area = max(1, min_component_area)

    def process(
        self,
        class_map: np.ndarray,
        probabilities: np.ndarray,
        inference_time_ms: float,
    ) -> FrameVisionResult:
        if class_map.ndim != 2:
            raise ValueError(f"U-Net class map must be 2D, got {class_map.shape}")
        if probabilities.shape[1:] != class_map.shape:
            raise ValueError("U-Net probability and class map shapes differ")
        instances: list[DetectedInstance] = []
        for class_id, class_name in self.label_to_name.items():
            if class_id == 0 or class_name == "background":
                continue
            binary = (class_map == class_id).astype(np.uint8)
            component_count, labels, stats, centers = cv2.connectedComponentsWithStats(
                binary, connectivity=8
            )
            for component_id in range(1, component_count):
                x, y, width, height, area = stats[component_id]
                if int(area) < self.min_component_area:
                    continue
                mask = labels == component_id
                contours, _ = cv2.findContours(
                    mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                contour = max(contours, key=cv2.contourArea) if contours else None
                confidence = float(np.mean(probabilities[class_id][mask]))
                center_x, center_y = centers[component_id]
                instances.append(
                    DetectedInstance(
                        class_id=int(class_id),
                        class_name=class_name,
                        confidence=confidence,
                        bbox=(int(x), int(y), int(x + width), int(y + height)),
                        mask=mask,
                        contour=contour,
                        center=(float(center_x), float(center_y)),
                        area_px=int(area),
                    )
                )
        instances.sort(key=lambda item: (item.center[1], item.center[0], item.class_id))
        return FrameVisionResult(datetime.now(timezone.utc), instances, inference_time_ms)
