from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
import torchvision


logger = logging.getLogger(__name__)
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def _conv_bn(input_channels: int, output_channels: int) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv2d(input_channels, output_channels, 3, padding=1, bias=False),
        nn.BatchNorm2d(output_channels),
        nn.ReLU(inplace=True),
    )


class DecoderBlock(nn.Module):
    """Decoder used by the original training project."""

    def __init__(self, input_channels: int, skip_channels: int, output_channels: int) -> None:
        super().__init__()
        self.conv = nn.Sequential(
            _conv_bn(input_channels + skip_channels, output_channels),
            _conv_bn(output_channels, output_channels),
        )

    def forward(self, value: torch.Tensor, skip: torch.Tensor | None = None) -> torch.Tensor:
        value = F.interpolate(value, scale_factor=2, mode="nearest")
        if skip is not None:
            value = torch.cat((value, skip), dim=1)
        return self.conv(value)


class ResNet18UNet(nn.Module):
    """Checkpoint-compatible copy of the original ResNet U-Net."""

    def __init__(self, class_count: int, encoder_name: str = "resnet18") -> None:
        super().__init__()
        if encoder_name not in {"resnet18", "resnet34", "resnet50"}:
            raise ValueError(f"unsupported U-Net encoder: {encoder_name}")
        encoder = getattr(torchvision.models, encoder_name)(weights=None)
        self.stem = nn.Sequential(encoder.conv1, encoder.bn1, encoder.relu)
        self.pool = encoder.maxpool
        self.l1 = encoder.layer1
        self.l2 = encoder.layer2
        self.l3 = encoder.layer3
        self.l4 = encoder.layer4
        channels = (
            [64, 64, 128, 256, 512]
            if encoder_name in {"resnet18", "resnet34"}
            else [64, 256, 512, 1024, 2048]
        )
        self.d4 = DecoderBlock(channels[4], channels[3], 256)
        self.d3 = DecoderBlock(256, channels[2], 128)
        self.d2 = DecoderBlock(128, channels[1], 64)
        self.d1 = DecoderBlock(64, channels[0], 32)
        self.d0 = DecoderBlock(32, 0, 16)
        self.head = nn.Conv2d(16, class_count, 1)

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        stem = self.stem(value)
        level1 = self.l1(self.pool(stem))
        level2 = self.l2(level1)
        level3 = self.l3(level2)
        level4 = self.l4(level3)
        value = self.d4(level4, level3)
        value = self.d3(value, level2)
        value = self.d2(value, level1)
        value = self.d1(value, stem)
        value = self.d0(value)
        return self.head(value)


@dataclass(slots=True)
class UNetPrediction:
    frame: np.ndarray
    class_map: np.ndarray
    probabilities: np.ndarray
    crop_to_frame: np.ndarray
    inference_time_ms: float


class UNetSegPredictor:
    def __init__(
        self,
        fine_model_path: str,
        locator_model_path: str,
        device_name: str = "auto",
        locator_width: int = 512,
        fine_size: int = 512,
        roi_margin: float = 1.3,
        roi_min_side: int = 256,
        use_locator: bool = True,
        use_half: bool = True,
        roi_smooth: float = 0.5,
    ) -> None:
        self.device, self.device_name = self._resolve_device(device_name)
        self.locator_width = max(32, locator_width)
        self.fine_size = max(32, fine_size)
        self.roi_margin = max(1.0, roi_margin)
        self.roi_min_side = max(1, roi_min_side)
        self.use_amp = use_half and self.device.type == "cuda"
        self.roi_smooth = min(1.0, max(0.0, roi_smooth))
        self._previous_roi: tuple[float, float, float] | None = None
        self.fine_model, fine_meta = self._load_model(Path(fine_model_path), expected_stage="fine")
        self.class_count = int(fine_meta["n_classes"])
        self.encoder_name = str(fine_meta["encoder"])
        self.label_to_name = {0: "background", 1: "bolt", 2: "washer", 3: "thread"}
        if self.class_count != len(self.label_to_name):
            raise ValueError(f"U-Net class count must be 4, got {self.class_count}")
        self.locator_model: ResNet18UNet | None = None
        if use_locator:
            self.locator_model, locator_meta = self._load_model(
                Path(locator_model_path), expected_stage="locator"
            )
            if (
                int(locator_meta["n_classes"]) != self.class_count
                or locator_meta["encoder"] != self.encoder_name
            ):
                raise ValueError("U-Net locator and fine checkpoint metadata differ")
        logger.info(
            "U-Net loaded on %s (encoder=%s, fine=%s, locator=%s)",
            self.device_name,
            self.encoder_name,
            fine_model_path,
            locator_model_path if self.locator_model is not None else "disabled",
        )

    def predict(self, frame: np.ndarray) -> UNetPrediction:
        if frame is None or frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError("U-Net input must be a BGR image with three channels")
        started = time.perf_counter()
        working_frame = self._to_base_resolution(frame)
        if self.locator_model is None:
            small, matrix = self._locator_input(working_frame)
            probabilities = self._predict_probabilities(self.fine_model, small)
            class_map = probabilities.argmax(0).astype(np.uint8)
            crop_to_frame = cv2.invertAffineTransform(matrix)
        else:
            roi = self._locate(working_frame)
            if roi is None:
                self._previous_roi = None
                class_map = np.zeros((self.fine_size, self.fine_size), dtype=np.uint8)
                probabilities = np.zeros(
                    (self.class_count, self.fine_size, self.fine_size), dtype=np.float32
                )
                probabilities[0] = 1.0
                crop_to_frame = np.array(
                    [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float64
                )
                if self.device.type == "cuda":
                    torch.cuda.synchronize(self.device)
                return UNetPrediction(
                    working_frame,
                    class_map,
                    probabilities,
                    crop_to_frame,
                    (time.perf_counter() - started) * 1000.0,
                )
            if self._previous_roi is not None:
                alpha = self.roi_smooth
                roi = tuple(
                    alpha * previous + (1.0 - alpha) * current
                    for previous, current in zip(self._previous_roi, roi)
                )
            self._previous_roi = roi
            matrix = self._crop_affine(*roi, self.fine_size)
            crop = cv2.warpAffine(
                working_frame,
                matrix,
                (self.fine_size, self.fine_size),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_REPLICATE,
            )
            probabilities = self._predict_probabilities(self.fine_model, crop)
            class_map = probabilities.argmax(0).astype(np.uint8)
            crop_to_frame = cv2.invertAffineTransform(matrix)
        if self.device.type == "cuda":
            torch.cuda.synchronize(self.device)
        return UNetPrediction(
            working_frame,
            class_map,
            probabilities,
            crop_to_frame,
            (time.perf_counter() - started) * 1000.0,
        )

    def _predict_probabilities(
        self, model: ResNet18UNet, image_bgr: np.ndarray
    ) -> np.ndarray:
        rgb = image_bgr[..., ::-1].copy()
        normalized = (rgb.astype(np.float32) / 255.0 - IMAGENET_MEAN) / IMAGENET_STD
        tensor = (
            torch.from_numpy(normalized)
            .permute(2, 0, 1)
            .unsqueeze(0)
            .to(self.device)
        )
        with torch.inference_mode(), torch.autocast(
            self.device.type, enabled=self.use_amp
        ):
            logits = model(tensor)
        return logits.float().softmax(1)[0].cpu().numpy()

    def _locate(self, frame: np.ndarray) -> tuple[float, float, float] | None:
        small, _ = self._locator_input(frame)
        probabilities = self._predict_probabilities(self.locator_model, small)
        foreground = (probabilities.argmax(0) > 0).astype(np.uint8)
        component_count, _, stats, _ = cv2.connectedComponentsWithStats(foreground)
        if component_count <= 1:
            return None
        areas = stats[1:, cv2.CC_STAT_AREA]
        largest = int(np.argmax(areas))
        if areas[largest] < 20:
            return None
        boxes = [
            (x, y, x + width, y + height)
            for x, y, width, height in stats[1:, :4]
        ]
        reach = max(
            boxes[largest][2] - boxes[largest][0],
            boxes[largest][3] - boxes[largest][1],
        )
        candidates = {
            index
            for index in range(component_count - 1)
            if index != largest and areas[index] >= max(8, 0.05 * areas[largest])
        }
        x0, y0, x1, y1 = boxes[largest]
        grown = True
        while grown:
            grown = False
            for index in sorted(candidates):
                bx0, by0, bx1, by1 = boxes[index]
                gap = max(bx0 - x1, x0 - bx1, by0 - y1, y0 - by1, 0)
                if gap <= reach:
                    x0, y0, x1, y1 = (
                        min(x0, bx0),
                        min(y0, by0),
                        max(x1, bx1),
                        max(y1, by1),
                    )
                    candidates.discard(index)
                    grown = True
        frame_height, frame_width = frame.shape[:2]
        small_height, small_width = small.shape[:2]
        return self._square_roi(
            x0 * frame_width / small_width,
            y0 * frame_height / small_height,
            x1 * frame_width / small_width,
            y1 * frame_height / small_height,
            frame_width,
            frame_height,
        )

    def _locator_input(self, frame: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        height, width = frame.shape[:2]
        output_width = self.locator_width
        output_height = max(
            32, int(round(output_width * height / width / 32)) * 32
        )
        small = cv2.resize(
            frame, (output_width, output_height), interpolation=cv2.INTER_AREA
        )
        return small, np.array(
            [
                [output_width / width, 0.0, 0.0],
                [0.0, output_height / height, 0.0],
            ],
            dtype=np.float64,
        )

    def _square_roi(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        image_width: int,
        image_height: int,
    ) -> tuple[float, float, float]:
        center_x, center_y = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        side = max(
            max(x1 - x0, y1 - y0) * self.roi_margin, self.roi_min_side
        )
        return center_x, center_y, min(side, max(image_width, image_height))

    @staticmethod
    def _crop_affine(
        center_x: float, center_y: float, side: float, output_size: int
    ) -> np.ndarray:
        scale = output_size / side
        matrix = cv2.getRotationMatrix2D((center_x, center_y), 0.0, scale)
        matrix[:, 2] += output_size / 2.0 - np.array([center_x, center_y])
        return matrix

    @staticmethod
    def _to_base_resolution(frame: np.ndarray) -> np.ndarray:
        height, width = frame.shape[:2]
        if width <= 1920:
            return frame
        scale = 1920.0 / width
        return cv2.resize(
            frame, (1920, round(height * scale)), interpolation=cv2.INTER_AREA
        )

    def _load_model(
        self, path: Path, *, expected_stage: str
    ) -> tuple[ResNet18UNet, dict]:
        if not path.is_file():
            raise FileNotFoundError(f"U-Net model not found: {path}")
        safe_globals = [
            np._core.multiarray.scalar,
            np.dtype,
            type(np.dtype(np.float64)),
        ]
        with torch.serialization.safe_globals(safe_globals):
            checkpoint = torch.load(path, map_location="cpu", weights_only=True)
        required = {"model", "encoder", "n_classes", "stage"}
        if not isinstance(checkpoint, dict) or not required.issubset(checkpoint):
            raise ValueError(f"invalid U-Net checkpoint: {path}")
        if checkpoint["stage"] != expected_stage:
            raise ValueError(
                f"unexpected U-Net checkpoint stage: {checkpoint['stage']!r}"
            )
        model = ResNet18UNet(
            int(checkpoint["n_classes"]), str(checkpoint["encoder"])
        )
        model.load_state_dict(checkpoint["model"], strict=True)
        return model.to(self.device).eval(), checkpoint

    @staticmethod
    def _resolve_device(device_name: str) -> tuple[torch.device, str]:
        requested = device_name.strip().lower()
        if requested == "auto":
            device = torch.device(
                "cuda:0" if torch.cuda.is_available() else "cpu"
            )
            return device, str(device)
        if requested.startswith("cuda") and not torch.cuda.is_available():
            logger.warning("CUDA requested but unavailable; falling back to CPU")
            return torch.device("cpu"), "cpu"
        if requested == "cpu" or requested.startswith("cuda"):
            device = torch.device(requested)
            return device, str(device)
        raise ValueError(f"invalid VISION_DEVICE: {device_name}")
