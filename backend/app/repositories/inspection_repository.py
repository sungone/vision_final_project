from __future__ import annotations

from app.database import db
from app.models import Inspection


class InspectionRepository:
    def add(
        self,
        inspection: Inspection,
    ) -> Inspection:
        db.session.add(inspection)
        db.session.commit()
        return inspection

    def delete(
        self,
        inspection: Inspection,
    ) -> None:
        db.session.delete(inspection)
        db.session.commit()

    def rollback(self) -> None:
        db.session.rollback()

    def latest(self) -> Inspection | None:
        statement = (
            db.select(Inspection)
            .order_by(
                Inspection.inspection_time.desc(),
                Inspection.id.desc(),
            )
            .limit(1)
        )

        return db.session.execute(
            statement,
        ).scalar_one_or_none()

    def get(
        self,
        inspection_id: int,
    ) -> Inspection | None:
        return db.session.get(
            Inspection,
            inspection_id,
        )

    def get_by_event_key(
        self,
        event_key: str,
    ) -> Inspection | None:
        statement = (
            db.select(Inspection)
            .where(
                Inspection.event_key == event_key,
            )
            .limit(1)
        )

        return db.session.execute(
            statement,
        ).scalar_one_or_none()

    def list_page(
        self,
        page: int,
        size: int,
    ) -> tuple[list[Inspection], int]:
        statement = db.select(
            Inspection,
        ).order_by(
            Inspection.inspection_time.desc(),
            Inspection.id.desc(),
        )

        pagination = db.paginate(
            statement,
            page=page + 1,
            per_page=size,
            error_out=False,
        )

        return (
            list(pagination.items),
            pagination.total,
        )