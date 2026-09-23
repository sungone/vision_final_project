from __future__ import annotations

from datetime import datetime, timezone

import cv2
import numpy as np

from .contracts import InspectionResult, NORMAL


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

