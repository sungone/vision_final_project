from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from app.database import db


json_type = JSON().with_variant(JSONB(), "postgresql")


class Inspection(db.Model):
    __tablename__ = "inspections"

    id = db.Column(Integer, primary_key=True, autoincrement=True)
    inspection_time = db.Column(DateTime(timezone=True), nullable=False, index=True)
    overall_result = db.Column(String(20), nullable=False, index=True)
    missing_component_result = db.Column(String(20), nullable=False)
    alignment_result = db.Column(String(20), nullable=False)
    fastening_result = db.Column(String(20), nullable=False)
    metrics = db.Column(json_type, nullable=False, default=dict)
    defect_image_path = db.Column(Text, nullable=True)
    event_key = db.Column(String(120), nullable=True, unique=True)
    created_at = db.Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self, include_image_url: bool = True) -> dict:
        result = {
            "id": self.id,
            "inspectionTime": _iso(self.inspection_time),
            "overallResult": self.overall_result,
            "missingComponentResult": self.missing_component_result,
            "alignmentResult": self.alignment_result,
            "fasteningResult": self.fastening_result,
            "metrics": self.metrics or {},
            "createdAt": _iso(self.created_at),
        }
        if include_image_url:
            result["defectImageUrl"] = (
                f"/api/v1/inspections/{self.id}/image" if self.defect_image_path else None
            )
        return result


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()

