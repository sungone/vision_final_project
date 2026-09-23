from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
from torchvision.models.detection import maskrcnn_resnet50_fpn_v2
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor as TorchvisionMaskRCNNPredictor


logger = logging.getLogger(__name__)


class MaskRCNNPredictor:
    def __init__(self, model_path: str, metadata_path: str, device_name: str = "auto") -> None:
        self.model_path = Path(model_path)
        self.metadata_path = Path(metadata_path)
        self.metadata = self._load_metadata()
        self.device = self._resolve_device(device_name)
        self.label_to_name = {int(key): value for key, value in self.metadata["label_to_name"].items()}
        self.model = self._load_model()

    def predict(self, frame: np.ndarray) -> tuple[dict[str, torch.Tensor], float]:
        if frame is None or frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError("Mask R-CNN input must be a BGR image with three channels")
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(np.ascontiguousarray(rgb)).permute(2, 0, 1).float().div_(255.0)
        tensor = tensor.to(self.device)
        started = time.perf_counter()
        with torch.inference_mode():
            prediction = self.model([tensor])[0]
        if self.device.type == "cuda":
            torch.cuda.synchronize(self.device)
        return prediction, (time.perf_counter() - started) * 1000.0

    def _load_metadata(self) -> dict[str, Any]:
        if not self.metadata_path.is_file():
            raise FileNotFoundError(f"model metadata not found: {self.metadata_path}")
        metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        required = {"architecture", "num_classes", "label_to_name", "min_size", "max_size"}
        missing = required.difference(metadata)
        if missing:
            raise ValueError(f"model metadata is missing keys: {sorted(missing)}")
        if metadata["architecture"] != "maskrcnn_resnet50_fpn_v2":
            raise ValueError(f"unsupported architecture: {metadata['architecture']}")
        return metadata

    def _load_model(self):
        if not self.model_path.is_file():
            raise FileNotFoundError(f"Mask R-CNN model not found: {self.model_path}")
        num_classes = int(self.metadata["num_classes"])
        model = maskrcnn_resnet50_fpn_v2(
            weights=None, weights_backbone=None,
            min_size=int(self.metadata["min_size"]), max_size=int(self.metadata["max_size"]),
        )
        box_features = model.roi_heads.box_predictor.cls_score.in_features
        model.roi_heads.box_predictor = FastRCNNPredictor(box_features, num_classes)
        mask_features = model.roi_heads.mask_predictor.conv5_mask.in_channels
        model.roi_heads.mask_predictor = TorchvisionMaskRCNNPredictor(mask_features, 256, num_classes)
        state_dict = torch.load(self.model_path, map_location="cpu", weights_only=True)
        if not isinstance(state_dict, dict) or "roi_heads.box_predictor.cls_score.weight" not in state_dict:
            raise ValueError("model file is not the expected Mask R-CNN state_dict")
        model.load_state_dict(state_dict, strict=True)
        model.to(self.device)
        model.eval()
        logger.info("Mask R-CNN loaded from %s on %s", self.model_path, self.device)
        return model

    @staticmethod
    def _resolve_device(device_name: str) -> torch.device:
        requested = device_name.strip().lower()
        if requested == "auto":
            return torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if requested.startswith("cuda") and not torch.cuda.is_available():
            logger.warning("CUDA was requested but is unavailable; falling back to CPU")
            return torch.device("cpu")
        try:
            return torch.device(requested)
        except (RuntimeError, ValueError) as exc:
            raise ValueError(f"invalid VISION_DEVICE: {device_name}") from exc
