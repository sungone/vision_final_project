from __future__ import annotations

import cv2
import numpy as np

from .contracts import FrameVisionResult


CLASS_COLORS: dict[str, tuple[int, int, int]] = {
    "bolt": (255, 0, 0),
    "washer": (0, 255, 255),
    "thread": (255, 0, 0),
}
DISPLAY_NAMES = {"bolt": "Bolt", "washer": "Washer", "thread": "Thread/Nut"}


class InspectionVisualizer:
    def __init__(self, overlay_alpha: float = 0.45, draw_boxes: bool = True, draw_stats: bool = True) -> None:
        self.overlay_alpha = min(1.0, max(0.0, overlay_alpha))
        self.draw_boxes = draw_boxes
        self.draw_stats = draw_stats

    def render(self, frame: np.ndarray, result: FrameVisionResult) -> np.ndarray:
        output = frame.copy()
        overlay = output.copy()
        for instance in result.instances:
            overlay[instance.mask] = CLASS_COLORS.get(instance.class_name, (0, 255, 0))
        output = cv2.addWeighted(overlay, self.overlay_alpha, output, 1.0 - self.overlay_alpha, 0)
        for instance in result.instances:
            color = CLASS_COLORS.get(instance.class_name, (0, 255, 0))
            if instance.contour is not None:
                cv2.drawContours(output, [instance.contour], -1, color, 2)
            x1, y1, x2, y2 = instance.bbox
            if self.draw_boxes:
                cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
            label = f"{DISPLAY_NAMES.get(instance.class_name, instance.class_name)} {instance.confidence:.2f}"
            self._draw_label(output, label, x1, y1, color)
        if self.draw_stats:
            text = f"Instances: {len(result.instances)} | Inference: {result.inference_time_ms:.1f} ms"
            cv2.rectangle(output, (8, 8), (450, 42), (0, 0, 0), -1)
            cv2.putText(output, text, (18, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 1)
        return output

    @staticmethod
    def _draw_label(frame: np.ndarray, text: str, x: int, y: int, color: tuple[int, int, int]) -> None:
        (width, height), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
        top = max(0, y - height - baseline - 8)
        cv2.rectangle(frame, (x, top), (x + width + 10, top + height + baseline + 8), color, -1)
        cv2.putText(frame, text, (x + 5, top + height + 3), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
