from __future__ import annotations

import math
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    request,
    send_file,
)

from app.repositories import InspectionRepository


bp = Blueprint("inspections", __name__)


def _repository() -> InspectionRepository:
    return InspectionRepository()


@bp.get("/api/v1/inspection/latest")
def latest_inspection():
    runtime = current_app.extensions[
        "vision_runtime"
    ]

    snapshot = runtime.latest_results.get(
        timeout=0,
    )

    if snapshot is None:
        return "", 204

    return jsonify(
        snapshot.value.to_live_dict(),
    )


@bp.get("/api/v1/inspections")
def list_inspections():
    page = request.args.get(
        "page",
        default=0,
        type=int,
    )

    size = request.args.get(
        "size",
        default=20,
        type=int,
    )

    if (
        page is None
        or page < 0
        or size is None
        or size < 1
        or size > 100
    ):
        return (
            jsonify(
                {
                    "error": "invalid_pagination",
                    "message": (
                        "page must be >= 0 and "
                        "size must be between 1 and 100"
                    ),
                }
            ),
            400,
        )

    items, total = (
        _repository().list_page(
            page,
            size,
        )
    )

    return jsonify(
        {
            "content": [
                item.to_dict()
                for item in items
            ],
            "page": page,
            "size": size,
            "totalElements": total,
            "totalPages": (
                math.ceil(total / size)
                if total
                else 0
            ),
        }
    )


@bp.get(
    "/api/v1/inspections/"
    "<int:inspection_id>"
)
def inspection_detail(
    inspection_id: int,
):
    record = _repository().get(
        inspection_id,
    )

    if record is None:
        abort(
            404,
            description=(
                "Inspection record not found."
            ),
        )

    return jsonify(record.to_dict())


@bp.delete(
    "/api/v1/inspections/"
    "<int:inspection_id>"
)
def delete_inspection(
    inspection_id: int,
):
    repository = _repository()

    record = repository.get(
        inspection_id,
    )

    if record is None:
        abort(
            404,
            description=(
                "Inspection record not found."
            ),
        )

    image_path = _resolve_safe_image_path(
        record.defect_image_path,
    )

    repository.delete(record)

    image_deleted = False

    if (
        image_path is not None
        and image_path.is_file()
    ):
        try:
            image_path.unlink()
            image_deleted = True
        except OSError:
            current_app.logger.exception(
                "Inspection %s was deleted "
                "but its evidence image "
                "could not be removed.",
                inspection_id,
            )

    return jsonify(
        {
            "deleted": True,
            "inspectionId": inspection_id,
            "imageDeleted": image_deleted,
        }
    )


@bp.get(
    "/api/v1/inspections/"
    "<int:inspection_id>/image"
)
def inspection_image(
    inspection_id: int,
):
    record = _repository().get(
        inspection_id,
    )

    if (
        record is None
        or not record.defect_image_path
    ):
        abort(
            404,
            description=(
                "Inspection image not found."
            ),
        )

    image_path = _resolve_safe_image_path(
        record.defect_image_path,
    )

    if (
        image_path is None
        or not image_path.is_file()
    ):
        abort(
            404,
            description=(
                "Inspection image not found."
            ),
        )

    return send_file(
        image_path,
        conditional=True,
    )


def _resolve_safe_image_path(
    stored_path: str | None,
) -> Path | None:
    if not stored_path:
        return None

    storage_root = Path(
        current_app.config[
            "DEFECT_STORAGE_DIR"
        ]
    ).resolve()

    image_path = Path(
        stored_path,
    ).resolve()

    if storage_root not in image_path.parents:
        current_app.logger.warning(
            "Rejected inspection image path "
            "outside storage root: %s",
            image_path,
        )

        return None

    return image_path