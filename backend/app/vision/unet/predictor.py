from __future__ import annotations

import logging
import time
from pathlib import Path

import cv2
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from torchvision.models import resnet18


logger = logging.getLogger(__name__)
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


class DecoderBlock(nn.Module):
    def __init__(self, input_channels: int, output_channels: int) -> None:
        super().__init__()
        self.conv = nn.Sequential(
            nn.Sequential(
                nn.Conv2d(input_channels, output_channels, 3, padding=1, bias=False),
                nn.BatchNorm2d(output_channels),
                nn.ReLU(inplace=True),
            ),
            nn.Sequential(
                nn.Conv2d(output_channels, output_channels, 3, padding=1, bias=False),
                nn.BatchNorm2d(output_channels),
                nn.ReLU(inplace=True),
            ),
        )

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return self.conv(value)


class ResNet18UNet(nn.Module):
    """Architecture reconstructed from the project's U-Net checkpoint keys."""

    def __init__(self, class_count: int) -> None:
        super().__init__()
        encoder = resnet18(weights=None)
        self.stem = nn.Sequential(encoder.conv1, encoder.bn1, encoder.relu)
        self.pool = encoder.maxpool
        self.l1 = encoder.layer1
        self.l2 = encoder.layer2
        self.l3 = encoder.layer3
        self.l4 = encoder.layer4
        self.d4 = DecoderBlock(512 + 256, 256)
        self.d3 = DecoderBlock(256 + 128, 128)
        self.d2 = DecoderBlock(128 + 64, 64)
        self.d1 = DecoderBlock(64 + 64, 32)
        self.d0 = DecoderBlock(32, 16)
        self.head = nn.Conv2d(16, class_count, 1)

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        stem = self.stem(value)
        level1 = self.l1(self.pool(stem))
        level2 = self.l2(level1)
        level3 = self.l3(level2)
        level4 = self.l4(level3)
        decoded4 = self.d4(torch.cat((self._up(level4, level3), level3), dim=1))
        decoded3 = self.d3(torch.cat((self._up(decoded4, level2), level2), dim=1))
        decoded2 = self.d2(torch.cat((self._up(decoded3, level1), level1), dim=1))
        decoded1 = self.d1(torch.cat((self._up(decoded2, stem), stem), dim=1))
        decoded0 = self.d0(F.interpolate(decoded1, size=value.shape[-2:], mode="bilinear", align_corners=False))
        return self.head(decoded0)

    @staticmethod
    def _up(value: torch.Tensor, skip: torch.Tensor) -> torch.Tensor:
        return F.interpolate(value, size=skip.shape[-2:], mode="bilinear", align_corners=False)


class UNetSegPredictor:
    def __init__(
        self,
        fine_model_path: str,
        locator_model_path: str,
        device_name: str = "auto",
        image_size: int = 640,
        roi_margin_ratio: float = 0.15,
        use_locator: bool = True,
        use_half: bool = True,
    ) -> None:
        self.device, self.device_name = self._resolve_device(device_name)
        self.image_size = max(32, image_size)
        self.roi_margin_ratio = max(0.0, roi_margin_ratio)
        self.use_half = use_half and self.device.type == "cuda"
        self.fine_model, fine_meta = self._load_model(Path(fine_model_path), expected_stage="fine")
        self.class_count = int(fine_meta["n_classes"])
        self.label_to_name = {0: "background", 1: "bolt", 2: "washer", 3: "thread"}
        if self.class_count != len(self.label_to_name):
            raise ValueError(f"U-Net class count must be 4, got {self.class_count}")
        self.locator_model: ResNet18UNet | None = None
        if use_locator:
            self.locator_model, locator_meta = self._load_model(
                Path(locator_model_path), expected_stage="locator"
            )
            if int(locator_meta["n_classes"]) != self.class_count:
                raise ValueError("U-Net locator and fine class counts differ")
        logger.info(
            "U-Net loaded on %s (fine=%s, locator=%s)",
            self.device_name,
            fine_model_path,
            locator_model_path if self.locator_model is not None else "disabled",
        )

    def predict(self, frame: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
        if frame is None or frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError("U-Net input must be a BGR image with three channels")
        started = time.perf_counter()
        if self.locator_model is None:
            class_map, probabilities = self._predict_map(frame, self.fine_model)
        else:
            locator_map, _ = self._predict_map(frame, self.locator_model)
            roi = self._foreground_roi(locator_map, frame.shape)
            if roi is None:
                class_map, probabilities = self._predict_map(frame, self.fine_model)
            else:
                x1, y1, x2, y2 = roi
                crop_map, crop_probabilities = self._predict_map(frame[y1:y2, x1:x2], self.fine_model)
                height, width = frame.shape[:2]
                class_map = np.zeros((height, width), dtype=np.uint8)
                probabilities = np.zeros((self.class_count, height, width), dtype=np.float32)
                class_map[y1:y2, x1:x2] = crop_map
                probabilities[:, y1:y2, x1:x2] = crop_probabilities
                probabilities[0, :y1, :] = 1.0
                probabilities[0, y2:, :] = 1.0
                probabilities[0, y1:y2, :x1] = 1.0
                probabilities[0, y1:y2, x2:] = 1.0
        if self.device.type == "cuda":
            torch.cuda.synchronize(self.device)
        return class_map, probabilities, (time.perf_counter() - started) * 1000.0

    def _predict_map(
        self, frame: np.ndarray, model: ResNet18UNet
    ) -> tuple[np.ndarray, np.ndarray]:
        height, width = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (self.image_size, self.image_size), interpolation=cv2.INTER_LINEAR)
        normalized = (resized.astype(np.float32) / 255.0 - IMAGENET_MEAN) / IMAGENET_STD
        tensor = torch.from_numpy(np.ascontiguousarray(normalized)).permute(2, 0, 1).unsqueeze(0)
        tensor = tensor.to(self.device)
        if self.use_half:
            tensor = tensor.half()
        with torch.inference_mode():
            logits = model(tensor)
            probabilities = torch.softmax(logits.float(), dim=1)[0].cpu().numpy()
        resized_probabilities = np.stack(
            [cv2.resize(channel, (width, height), interpolation=cv2.INTER_LINEAR) for channel in probabilities]
        )
        class_map = np.argmax(resized_probabilities, axis=0).astype(np.uint8)
        return class_map, resized_probabilities

    def _foreground_roi(
        self, class_map: np.ndarray, frame_shape: tuple[int, ...]
    ) -> tuple[int, int, int, int] | None:
        foreground = (class_map != 0).astype(np.uint8)
        points = cv2.findNonZero(foreground)
        if points is None:
            return None
        x, y, width, height = cv2.boundingRect(points)
        frame_height, frame_width = frame_shape[:2]
        margin = int(round(max(width, height) * self.roi_margin_ratio))
        return (
            max(0, x - margin),
            max(0, y - margin),
            min(frame_width, x + width + margin),
            min(frame_height, y + height + margin),
        )

    def _load_model(self, path: Path, *, expected_stage: str) -> tuple[ResNet18UNet, dict]:
        if not path.is_file():
            raise FileNotFoundError(f"U-Net model not found: {path}")
        safe_globals = [np._core.multiarray.scalar, np.dtype, type(np.dtype(np.float64))]
        with torch.serialization.safe_globals(safe_globals):
            checkpoint = torch.load(path, map_location="cpu", weights_only=True)
        required = {"model", "encoder", "n_classes", "stage"}
        if not isinstance(checkpoint, dict) or not required.issubset(checkpoint):
            raise ValueError(f"invalid U-Net checkpoint: {path}")
        if checkpoint["encoder"] != "resnet18" or checkpoint["stage"] != expected_stage:
            raise ValueError(
                f"unexpected U-Net checkpoint metadata: encoder={checkpoint['encoder']!r}, "
                f"stage={checkpoint['stage']!r}"
            )
        model = ResNet18UNet(int(checkpoint["n_classes"]))
        model.load_state_dict(checkpoint["model"], strict=True)
        model.to(self.device).eval()
        if self.use_half:
            model.half()
        return model, checkpoint

    @staticmethod
    def _resolve_device(device_name: str) -> tuple[torch.device, str]:
        requested = device_name.strip().lower()
        if requested == "auto":
            device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
            return device, str(device)
        if requested.startswith("cuda") and not torch.cuda.is_available():
            logger.warning("CUDA requested but unavailable; falling back to CPU")
            return torch.device("cpu"), "cpu"
        if requested == "cpu" or requested.startswith("cuda"):
            device = torch.device(requested)
            return device, str(device)
        raise ValueError(f"invalid VISION_DEVICE: {device_name}")
