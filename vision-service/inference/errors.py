class VisionServiceError(Exception):
    """Expected service failure that can be safely returned to the caller."""

    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class InvalidImageError(VisionServiceError):
    def __init__(self, message: str = "The uploaded file is not a valid supported image.") -> None:
        super().__init__("INVALID_IMAGE", message, 400)


class ImageTooLargeError(VisionServiceError):
    def __init__(self, message: str = "The uploaded image exceeds the configured size limit.") -> None:
        super().__init__("IMAGE_TOO_LARGE", message, 413)


class ModelNotAvailableError(VisionServiceError):
    def __init__(self, message: str = "The segmentation model is not available.") -> None:
        super().__init__("MODEL_NOT_AVAILABLE", message, 503)


class VisionInferenceError(VisionServiceError):
    def __init__(self, message: str = "Vision inference failed.") -> None:
        super().__init__("VISION_INFERENCE_FAILED", message, 500)
