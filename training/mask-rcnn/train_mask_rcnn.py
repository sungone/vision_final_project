from __future__ import annotations

import argparse
import json
import random
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
import torchvision
from PIL import Image
from pycocotools import mask as mask_utils
from torch.utils.data import DataLoader, Dataset
from torchvision.models.detection import MaskRCNN_ResNet50_FPN_V2_Weights
from torchvision.models.detection import maskrcnn_resnet50_fpn_v2
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.models.detection.mask_rcnn import MaskRCNNPredictor
from torchvision.transforms import functional as TF
from tqdm.auto import tqdm


class CocoPolygonMaskDataset(Dataset):
    def __init__(
        self,
        image_dir: Path,
        annotation_file: Path,
        image_ids: list[int],
        augment: bool,
    ) -> None:
        self.image_dir = image_dir
        data = json.loads(annotation_file.read_text(encoding="utf-8"))
        self.images = {item["id"]: item for item in data["images"]}
        self.categories = sorted(data["categories"], key=lambda item: item["id"])
        self.cat_to_label = {
            category["id"]: index + 1
            for index, category in enumerate(self.categories)
        }
        self.label_to_name = {
            index + 1: category["name"]
            for index, category in enumerate(self.categories)
        }
        self.annotations_by_image: dict[int, list[dict]] = defaultdict(list)
        for annotation in data["annotations"]:
            self.annotations_by_image[annotation["image_id"]].append(annotation)
        self.image_ids = image_ids
        self.augment = augment

    def __len__(self) -> int:
        return len(self.image_ids)

    @staticmethod
    def _decode_mask(segmentation, height: int, width: int) -> np.ndarray:
        if isinstance(segmentation, list):
            rle = mask_utils.merge(mask_utils.frPyObjects(segmentation, height, width))
        elif isinstance(segmentation, dict) and isinstance(segmentation.get("counts"), list):
            rle = mask_utils.frPyObjects(segmentation, height, width)
        else:
            rle = segmentation
        mask = mask_utils.decode(rle)
        if mask.ndim == 3:
            mask = np.any(mask, axis=2)
        return mask.astype(np.uint8)

    def __getitem__(self, index: int):
        image_id = self.image_ids[index]
        image_info = self.images[image_id]
        image_path = self.image_dir / image_info["file_name"]
        image = Image.open(image_path).convert("RGB")
        width, height = image.size

        boxes: list[list[float]] = []
        labels: list[int] = []
        masks: list[np.ndarray] = []
        areas: list[float] = []
        crowds: list[int] = []
        for annotation in self.annotations_by_image[image_id]:
            mask = self._decode_mask(annotation["segmentation"], height, width)
            ys, xs = np.where(mask > 0)
            if len(xs) == 0 or len(ys) == 0:
                continue
            x1, x2 = float(xs.min()), float(xs.max() + 1)
            y1, y2 = float(ys.min()), float(ys.max() + 1)
            if x2 <= x1 or y2 <= y1:
                continue
            boxes.append([x1, y1, x2, y2])
            labels.append(self.cat_to_label[annotation["category_id"]])
            masks.append(mask)
            areas.append(float(mask.sum()))
            crowds.append(int(annotation.get("iscrowd", 0)))

        image_tensor = TF.to_tensor(image)
        target = {
            "boxes": torch.tensor(boxes, dtype=torch.float32).reshape(-1, 4),
            "labels": torch.tensor(labels, dtype=torch.int64),
            "masks": torch.as_tensor(
                np.stack(masks) if masks else np.zeros((0, height, width)),
                dtype=torch.uint8,
            ),
            "image_id": torch.tensor(image_id, dtype=torch.int64),
            "area": torch.tensor(areas, dtype=torch.float32),
            "iscrowd": torch.tensor(crowds, dtype=torch.int64),
        }

        if self.augment and random.random() < 0.5:
            image_tensor = torch.flip(image_tensor, dims=[2])
            target["masks"] = torch.flip(target["masks"], dims=[2])
            if len(target["boxes"]):
                old_boxes = target["boxes"].clone()
                target["boxes"][:, 0] = width - old_boxes[:, 2]
                target["boxes"][:, 2] = width - old_boxes[:, 0]
        return image_tensor, target


def collate_fn(batch):
    return tuple(zip(*batch))


def validate_data(annotation_file: Path, image_dir: Path) -> tuple[dict, list[int]]:
    data = json.loads(annotation_file.read_text(encoding="utf-8"))
    missing = [
        item["file_name"]
        for item in data["images"]
        if not (image_dir / item["file_name"]).is_file()
    ]
    if missing:
        raise FileNotFoundError(f"Missing {len(missing)} annotated images: {missing[:10]}")
    category_ids = {category["id"] for category in data["categories"]}
    invalid = [
        annotation["id"]
        for annotation in data["annotations"]
        if annotation["category_id"] not in category_ids
        or not annotation.get("segmentation")
    ]
    if invalid:
        raise ValueError(f"Invalid annotations: {invalid[:10]}")
    image_ids = [item["id"] for item in data["images"]]
    print(
        f"Validated {len(image_ids)} images, {len(data['annotations'])} annotations, "
        f"categories={[category['name'] for category in data['categories']]}"
    )
    return data, image_ids


def build_model(num_classes: int, min_size: int, max_size: int):
    model = maskrcnn_resnet50_fpn_v2(
        weights=MaskRCNN_ResNet50_FPN_V2_Weights.DEFAULT,
        min_size=min_size,
        max_size=max_size,
    )
    box_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(box_features, num_classes)
    mask_features = model.roi_heads.mask_predictor.conv5_mask.in_channels
    model.roi_heads.mask_predictor = MaskRCNNPredictor(
        mask_features, 256, num_classes
    )
    return model


def move_targets(targets, device):
    return [
        {key: value.to(device, non_blocking=True) for key, value in target.items()}
        for target in targets
    ]


def train_one_epoch(model, loader, optimizer, scaler, device, use_amp: bool) -> float:
    model.train()
    total_loss = 0.0
    progress = tqdm(loader, desc="train", leave=False)
    for images, targets in progress:
        images = [image.to(device, non_blocking=True) for image in images]
        targets = move_targets(targets, device)
        optimizer.zero_grad(set_to_none=True)
        with torch.amp.autocast(device_type="cuda", enabled=use_amp):
            loss_dict = model(images, targets)
            loss = sum(loss_dict.values())
        if not torch.isfinite(loss):
            raise RuntimeError(f"Non-finite loss: {loss_dict}")
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        value = float(loss.detach())
        total_loss += value
        progress.set_postfix(loss=f"{value:.4f}")
    return total_loss / max(1, len(loader))


@torch.inference_mode()
def mean_best_mask_iou(model, loader, device, score_threshold: float) -> float:
    model.eval()
    values: list[float] = []
    for images, targets in tqdm(loader, desc="validate", leave=False):
        outputs = model([image.to(device) for image in images])
        for output, target in zip(outputs, targets):
            keep = output["scores"].cpu() >= score_threshold
            predicted_masks = output["masks"].cpu()[keep, 0] >= 0.5
            predicted_labels = output["labels"].cpu()[keep]
            for ground_mask, ground_label in zip(
                target["masks"].bool(), target["labels"]
            ):
                candidates = predicted_masks[predicted_labels == ground_label]
                if len(candidates) == 0:
                    values.append(0.0)
                    continue
                intersection = (candidates & ground_mask).flatten(1).sum(1).float()
                union = (
                    (candidates | ground_mask)
                    .flatten(1)
                    .sum(1)
                    .float()
                    .clamp_min(1)
                )
                values.append(float((intersection / union).max()))
    return float(np.mean(values)) if values else 0.0


def save_checkpoint(
    path: Path,
    epoch: int,
    model,
    optimizer,
    categories: list[dict],
    cat_to_label: dict[int, int],
    history: list[dict],
    args,
) -> None:
    torch.save(
        {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "categories": categories,
            "cat_to_label": cat_to_label,
            "history": history,
            "config": vars(args),
        },
        path,
    )


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", type=Path, default=Path("images"))
    parser.add_argument(
        "--annotations", type=Path, default=Path("merged_annotations.json")
    )
    parser.add_argument("--output", type=Path, default=Path("output/mask_rcnn"))
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--learning-rate", type=float, default=0.0025)
    parser.add_argument("--weight-decay", type=float, default=0.0005)
    parser.add_argument("--min-size", type=int, default=640)
    parser.add_argument("--max-size", type=int, default=1024)
    parser.add_argument("--val-fraction", type=float, default=0.2)
    parser.add_argument("--score-threshold", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.images = args.images.resolve()
    args.annotations = args.annotations.resolve()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA is unavailable. Install a CUDA-enabled PyTorch build before training."
        )
    device = torch.device("cuda")
    print(f"torch={torch.__version__}, torchvision={torchvision.__version__}")
    print(f"device={torch.cuda.get_device_name(0)}")

    data, image_ids = validate_data(args.annotations, args.images)
    random.Random(args.seed).shuffle(image_ids)
    validation_count = max(1, round(len(image_ids) * args.val_fraction))
    validation_ids = image_ids[:validation_count]
    training_ids = image_ids[validation_count:]

    train_dataset = CocoPolygonMaskDataset(
        args.images, args.annotations, training_ids, augment=True
    )
    validation_dataset = CocoPolygonMaskDataset(
        args.images, args.annotations, validation_ids, augment=False
    )
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.workers,
        collate_fn=collate_fn,
        pin_memory=True,
    )
    validation_loader = DataLoader(
        validation_dataset,
        batch_size=1,
        shuffle=False,
        num_workers=args.workers,
        collate_fn=collate_fn,
        pin_memory=True,
    )

    num_classes = 1 + len(data["categories"])
    model = build_model(num_classes, args.min_size, args.max_size).to(device)
    optimizer = torch.optim.SGD(
        [parameter for parameter in model.parameters() if parameter.requires_grad],
        lr=args.learning_rate,
        momentum=0.9,
        weight_decay=args.weight_decay,
    )
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=4, gamma=0.1)
    scaler = torch.amp.GradScaler("cuda", enabled=True)

    print(f"train={len(train_dataset)}, validation={len(validation_dataset)}")
    history: list[dict] = []
    best_iou = -1.0
    for epoch in range(1, args.epochs + 1):
        started = time.time()
        train_loss = train_one_epoch(
            model, train_loader, optimizer, scaler, device, use_amp=True
        )
        validation_iou = mean_best_mask_iou(
            model, validation_loader, device, args.score_threshold
        )
        scheduler.step()
        row = {
            "epoch": epoch,
            "trainLoss": train_loss,
            "valMeanBestMaskIoU": validation_iou,
            "seconds": time.time() - started,
        }
        history.append(row)
        print(json.dumps(row, ensure_ascii=False))
        save_checkpoint(
            args.output / "last_checkpoint.pt",
            epoch,
            model,
            optimizer,
            data["categories"],
            train_dataset.cat_to_label,
            history,
            args,
        )
        if validation_iou > best_iou:
            best_iou = validation_iou
            save_checkpoint(
                args.output / "best_checkpoint.pt",
                epoch,
                model,
                optimizer,
                data["categories"],
                train_dataset.cat_to_label,
                history,
                args,
            )
        (args.output / "history.json").write_text(
            json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    model.load_state_dict(
        torch.load(
            args.output / "best_checkpoint.pt",
            map_location=device,
            weights_only=False,
        )["model_state_dict"]
    )
    torch.save(model.state_dict(), args.output / "mask_rcnn_state_dict.pt")
    metadata = {
        "architecture": "maskrcnn_resnet50_fpn_v2",
        "num_classes": num_classes,
        "categories": data["categories"],
        "cat_to_label": train_dataset.cat_to_label,
        "label_to_name": train_dataset.label_to_name,
        "min_size": args.min_size,
        "max_size": args.max_size,
        "score_threshold": args.score_threshold,
        "best_val_mean_best_mask_iou": best_iou,
    }
    (args.output / "model_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Training complete. Outputs: {args.output}")


if __name__ == "__main__":
    main()
