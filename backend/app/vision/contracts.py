from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

import numpy as np


NORMAL = "NORMAL"
DEFECT = "DEFECT"
NOT_EVALUATED = "NOT_EVALUATED"


@dataclass(slots=True)
class InspectionResult:
    overall_result: str = NORMAL
    missing_component_result: str = NORMAL
    alignment_result: str = NORMAL
    fastening_result: str = NORMAL
    metrics: dict[str, Any] = field(default_factory=dict)
    processed_frame: np.ndarray | None = None
    inspection_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_key: str | None = None

    @property
    def is_defect(self) -> bool:
        return self.overall_result == DEFECT

    def to_live_dict(self) -> dict[str, Any]:
        return {
            "inspectionTime": self.inspection_time.isoformat(),
            "overallResult": self.overall_result,
            "missingComponentResult": self.missing_component_result,
            "alignmentResult": self.alignment_result,
            "fasteningResult": self.fastening_result,
            "metrics": self.metrics,
        }


class VisionProcessor(Protocol):
    def process(self, frame: np.ndarray) -> InspectionResult: ...

