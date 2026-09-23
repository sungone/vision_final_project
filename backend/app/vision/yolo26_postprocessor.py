from __future__ import annotations

from datetime import datetime, timezone

import cv2
import numpy as np

from .contracts import DetectedInstance, FrameVisionResult


class YOLO26SegmentationPostProcessor:
    def __init__(self, label_to_name: dict[int, str], mask_threshold: float = 0.5) -> None:
        self.label_to_name = label_to_name
        self.mask_threshold = mask_threshold

    def process(self, result, inference_time_ms: float, frame_shape: tuple[int, ...]) -> FrameVisionResult:
        instances: list[DetectedInstance] = []
        if result.boxes is None or result.masks is None or len(result.boxes) == 0:
            return FrameVisionResult(datetime.now(timezone.utc), instances, inference_time_ms)

        boxes = result.boxes.xyxy.detach().cpu().numpy()
        labels = result.boxes.cls.detach().cpu().numpy().astype(np.int64)
        scores = result.boxes.conf.detach().cpu().numpy()
        masks = result.masks.data.detach().cpu().numpy()
        height, width = frame_shape[:2]

        for box, class_id, score, mask_probability in zip(boxes, labels, scores, masks):
            class_name = self.label_to_name.get(int(class_id))
            if class_name is None:
                continue
            if mask_probability.shape != (height, width):
                mask_probability = cv2.resize(mask_probability, (width, height), interpolation=cv2.INTER_LINEAR)
            binary_mask = mask_probability >= self.mask_threshold
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
                class_id=int(class_id),
                class_name=class_name,
                confidence=float(score),
                bbox=(x1, y1, x2, y2),
                mask=binary_mask,
                contour=contour,
                center=center,
                area_px=int(np.count_nonzero(binary_mask)),
            ))
        return FrameVisionResult(datetime.now(timezone.utc), instances, inference_time_ms)
