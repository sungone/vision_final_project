from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import cv2

from app.models import Inspection
from app.repositories import InspectionRepository
from app.vision.contracts import InspectionResult


class InspectionService:
    def __init__(self, repository: InspectionRepository, storage_dir: str) -> None:
        self.repository = repository
        self.storage_dir = Path(storage_dir).resolve()

    def persist_event(self, result: InspectionResult) -> Inspection:
        event_key = result.event_key or f"evt-{result.inspection_time.strftime('%Y%m%d%H%M%S%f')}-{uuid4().hex[:8]}"
        result.event_key = event_key
        existing = self.repository.get_by_event_key(event_key)
        if existing is not None:
            return existing
        image_path = self._save_defect_frame(result)
        record = Inspection(
            inspection_time=result.inspection_time,
            overall_result=result.overall_result,
            missing_component_result=result.missing_component_result,
            alignment_result=result.alignment_result,
            fastening_result=result.fastening_result,
            metrics=result.metrics or {},
            defect_image_path=image_path,
            event_key=event_key,
            created_at=datetime.now(timezone.utc),
        )
        try:
            return self.repository.add(record)
        except Exception:
            self.repository.rollback()
            if image_path:
                Path(image_path).unlink(missing_ok=True)
            raise

    def _save_defect_frame(self, result: InspectionResult) -> str | None:
        if result.processed_frame is None:
            return None
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        filename = f"defect_{result.inspection_time.strftime('%Y%m%dT%H%M%S_%f')}_{uuid4().hex[:8]}.jpg"
        path = (self.storage_dir / filename).resolve()
        if self.storage_dir not in path.parents:
            raise ValueError("invalid defect image path")
        ok, encoded = cv2.imencode(".jpg", result.processed_frame)
        if not ok:
            raise OSError("failed to encode defect image")
        try:
            path.write_bytes(encoded.tobytes())
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return str(path)
