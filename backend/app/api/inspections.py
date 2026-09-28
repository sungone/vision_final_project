from __future__ import annotations

import math
from pathlib import Path
import time
import cv2
import numpy as np

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    request,
    send_file,
)

from app.inspection import InspectionService
from app.repositories import InspectionRepository

bp = Blueprint("inspections", __name__)

ALLOWED_UPLOAD_TYPES = {
    "image/jpeg",
    "image/png",
}

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

@bp.post("/api/v1/inspections")
def create_inspection():
    uploaded_image = request.files.get("image")

    if (
        uploaded_image is None
        or not uploaded_image.filename
    ):
        return _upload_error(
            "missing_image",
            "검사할 이미지가 없습니다.",
            400,
        )

    content_type = (
        uploaded_image.mimetype or ""
    ).lower()

    if content_type not in ALLOWED_UPLOAD_TYPES:
        return _upload_error(
            "unsupported_image_type",
            "JPG, JPEG, PNG 이미지만 업로드할 수 있습니다.",
            415,
        )

    max_image_bytes = current_app.config[
        "MAX_UPLOAD_IMAGE_BYTES"
    ]

    image_bytes = uploaded_image.read(
        max_image_bytes + 1
    )

    if not image_bytes:
        return _upload_error(
            "empty_image",
            "업로드한 이미지가 비어 있습니다.",
            400,
        )

    if len(image_bytes) > max_image_bytes:
        return _upload_error(
            "image_too_large",
            "이미지 크기는 최대 10MB입니다.",
            413,
        )

    encoded_image = np.frombuffer(
        image_bytes,
        dtype=np.uint8,
    )

    frame = cv2.imdecode(
        encoded_image,
        cv2.IMREAD_COLOR,
    )

    if frame is None or frame.size == 0:
        return _upload_error(
            "invalid_image",
            "이미지 파일을 해석할 수 없습니다.",
            400,
        )

    runtime = current_app.extensions[
        "vision_runtime"
    ]

    processing_started_at = time.perf_counter()

    result = runtime.processor.process(frame)

    if result.processed_frame is None:
        result.processed_frame = frame

    if result.metrics is None:
        result.metrics = {}

    result.metrics["processingTimeMs"] = round(
        (
            time.perf_counter()
            - processing_started_at
        )
        * 1000.0,
        2,
    )

    record = InspectionService(
        InspectionRepository(),
        current_app.config[
            "DEFECT_STORAGE_DIR"
        ],
    ).persist_event(result)

    response_body = result.to_live_dict()

    response_body.update(
        {
            "inspectionId": record.id,
            "resultImageUrl": (
                f"/api/v1/inspections/"
                f"{record.id}/image"
            ),
        }
    )

    return jsonify(response_body), 201

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

def _upload_error(
    code: str,
    message: str,
    status_code: int,
):
    return (
        jsonify(
            {
                "error": code,
                "code": code,
                "message": message,
            }
        ),
        status_code,
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