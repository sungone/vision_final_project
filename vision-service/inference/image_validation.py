from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from inference.errors import ImageTooLargeError, InvalidImageError


_MAGIC_SIGNATURES = {
    "image/jpeg": lambda data: data.startswith(b"\xff\xd8\xff"),
    "image/png": lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/webp": lambda data: len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP",
}
_EXTENSION_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


@dataclass(frozen=True)
class ValidatedImage:
    image: Image.Image
    width: int
    height: int


def validate_image(
    data: bytes,
    content_type: str | None,
    filename: str | None,
    *,
    max_bytes: int,
    max_pixels: int,
    max_dimension: int,
) -> ValidatedImage:
    if not data:
        raise InvalidImageError("The uploaded image is empty.")
    if len(data) > max_bytes:
        raise ImageTooLargeError()
    if not filename:
        raise InvalidImageError("An image filename is required.")

    normalized_type = (content_type or "").split(";", 1)[0].strip().lower()
    extension_type = _EXTENSION_TYPES.get(Path(filename).suffix.lower())
    if extension_type is None:
        raise InvalidImageError("Supported image extensions are .jpg, .jpeg, .png, and .webp.")
    if extension_type != normalized_type:
        raise InvalidImageError("The filename extension does not match its declared image type.")
    signature_check = _MAGIC_SIGNATURES.get(normalized_type)
    if signature_check is None or not signature_check(data):
        raise InvalidImageError("The file content does not match its declared image type.")

    try:
        with Image.open(BytesIO(data)) as probe:
            probe.verify()
        with Image.open(BytesIO(data)) as decoded:
            width, height = decoded.size
            if width <= 0 or height <= 0:
                raise InvalidImageError("The uploaded image has invalid dimensions.")
            if width > max_dimension or height > max_dimension or width * height > max_pixels:
                raise ImageTooLargeError("The uploaded image dimensions exceed the configured limit.")
            image = decoded.convert("RGB").copy()
    except Image.DecompressionBombError as exc:
        raise ImageTooLargeError("The uploaded image dimensions exceed the safe decoding limit.") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidImageError("The uploaded image could not be decoded.") from exc

    return ValidatedImage(image=image, width=width, height=height)
