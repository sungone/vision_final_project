from __future__ import annotations

from datetime import datetime, timezone

import cv2
import numpy as np

from ..contracts import DetectedInstance, FrameVisionResult
from .predictor import UNetPrediction


class UNetSegmentationPostProcessor:
    def __init__(self, label_to_name: dict[int, str], min_component_area: int = 50) -> None:
        self.label_to_name = label_to_name
        self.min_component_area = max(1, min_component_area)

    def process(
        self,
        class_map: np.ndarray,
        probabilities: np.ndarray,
        inference_time_ms: float,
        *,
        crop_to_frame: np.ndarray | None = None,
        frame_shape: tuple[int, ...] | None = None,
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
            binary = cv2.morphologyEx(
                binary, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)
            )
            component_count, labels, stats, centers = cv2.connectedComponentsWithStats(
                binary, connectivity=8
            )
            for component_id in range(1, component_count):
                x, y, width, height, area = stats[component_id]
                if int(area) < self.min_component_area:
                    continue
                crop_mask = labels == component_id
                mask = crop_mask
                geometry_points = np.column_stack(
                    np.nonzero(crop_mask)[::-1]
                ).astype(np.float32)
                if crop_to_frame is not None and frame_shape is not None:
                    frame_height, frame_width = frame_shape[:2]
                    mask = cv2.warpAffine(
                        crop_mask.astype(np.uint8),
                        crop_to_frame,
                        (frame_width, frame_height),
                        flags=cv2.INTER_NEAREST,
                    ).astype(bool)
                contours, _ = cv2.findContours(
                    mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                contour = max(contours, key=cv2.contourArea) if contours else None
                confidence = float(np.mean(probabilities[class_id][crop_mask]))
                frame_y, frame_x = np.nonzero(mask)
                if frame_x.size:
                    frame_x0, frame_x1 = int(frame_x.min()), int(frame_x.max() + 1)
                    frame_y0, frame_y1 = int(frame_y.min()), int(frame_y.max() + 1)
                    center_x, center_y = float(frame_x.mean()), float(frame_y.mean())
                    frame_area = int(frame_x.size)
                else:
                    frame_x0, frame_y0, frame_x1, frame_y1 = (
                        int(x), int(y), int(x + width), int(y + height)
                    )
                    center_x, center_y = centers[component_id]
                    frame_area = int(area)
                instances.append(
                    DetectedInstance(
                        class_id=int(class_id),
                        class_name=class_name,
                        confidence=confidence,
                        bbox=(frame_x0, frame_y0, frame_x1, frame_y1),
                        mask=mask,
                        contour=contour,
                        center=(float(center_x), float(center_y)),
                        area_px=frame_area,
                        geometry_points=geometry_points,
                    )
                )
        instances.sort(key=lambda item: (item.center[1], item.center[0], item.class_id))
        return FrameVisionResult(datetime.now(timezone.utc), instances, inference_time_ms)

    def process_prediction(self, prediction: UNetPrediction) -> FrameVisionResult:
        return self.process(
            prediction.class_map,
            prediction.probabilities,
            prediction.inference_time_ms,
            crop_to_frame=prediction.crop_to_frame,
            frame_shape=prediction.frame.shape,
        )
