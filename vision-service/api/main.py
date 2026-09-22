from __future__ import annotations

import os
import secrets
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from inference.errors import VisionServiceError
from inference.image_validation import validate_image
from inference.schemas import ErrorResponse, SegmentationResponse
from inference.yolo_service import YoloSegmentationService


def _positive_env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be positive")
    return value


def _model_path() -> Path:
    configured = os.getenv("MODEL_PATH")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[1] / "models" / "best.pt"


def create_app() -> FastAPI:
    app = FastAPI(title="Bolt Assembly Vision Service", version="1.0.0")
    app.state.max_image_bytes = _positive_env_int("MAX_IMAGE_BYTES", 10 * 1024 * 1024)
    app.state.max_image_pixels = _positive_env_int("MAX_IMAGE_PIXELS", 40_000_000)
    app.state.max_image_dimension = _positive_env_int("MAX_IMAGE_DIMENSION", 8_192)
    app.state.service_token = os.getenv("VISION_SERVICE_TOKEN")
    app.state.inference_service = YoloSegmentationService(
        _model_path(),
        max_total_polygon_points=_positive_env_int("MAX_TOTAL_POLYGON_POINTS", 200_000),
    )

    @app.exception_handler(VisionServiceError)
    async def vision_error_handler(_request: Request, exc: VisionServiceError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(code=exc.code, message=exc.message).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_request: Request, _exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(code="INVALID_REQUEST", message="The request parameters are invalid.").model_dump(),
        )

    @app.post(
        "/internal/v1/infer/segmentation",
        response_model=SegmentationResponse,
        responses={
            400: {"model": ErrorResponse},
            401: {"model": ErrorResponse},
            413: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
            503: {"model": ErrorResponse},
        },
    )
    async def infer_segmentation(
        request: Request,
        image: UploadFile = File(...),
        confidenceThreshold: float = Form(0.01, ge=0.0, le=1.0),
        service_token: str | None = Header(None, alias="X-Vision-Service-Token"),
    ) -> SegmentationResponse | JSONResponse:
        expected_token = request.app.state.service_token
        if expected_token and (service_token is None or not secrets.compare_digest(service_token, expected_token)):
            return JSONResponse(
                status_code=401,
                content=ErrorResponse(code="UNAUTHORIZED", message="A valid vision service token is required.").model_dump(),
            )

        data = await image.read(request.app.state.max_image_bytes + 1)
        validated = validate_image(
            data,
            image.content_type,
            image.filename,
            max_bytes=request.app.state.max_image_bytes,
            max_pixels=request.app.state.max_image_pixels,
            max_dimension=request.app.state.max_image_dimension,
        )
        return await run_in_threadpool(
            request.app.state.inference_service.predict,
            validated.image,
            confidenceThreshold,
        )

    return app


app = create_app()
