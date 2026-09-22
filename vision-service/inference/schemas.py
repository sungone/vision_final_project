from typing import Annotated

from pydantic import BaseModel, Field


Coordinate = Annotated[float, Field(allow_inf_nan=False)]
Point = Annotated[list[Coordinate], Field(min_length=2, max_length=2)]


class BoundingBox(BaseModel):
    x1: Coordinate
    y1: Coordinate
    x2: Coordinate
    y2: Coordinate


class Detection(BaseModel):
    className: str = Field(min_length=1, max_length=64)
    confidence: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    bbox: BoundingBox
    segmentation: list[Point] = Field(max_length=10_000)


class SegmentationResponse(BaseModel):
    modelVersion: str = Field(min_length=1, max_length=200)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    detections: list[Detection] = Field(max_length=1_000)


class ErrorResponse(BaseModel):
    code: str
    message: str
