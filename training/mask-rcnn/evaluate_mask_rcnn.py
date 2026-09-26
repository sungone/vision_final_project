from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
from pycocotools import mask as mask_utils
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval
from torch.utils.data import DataLoader
from tqdm.auto import tqdm


PROJECT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_DIR / "backend"
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.vision.mask_rcnn import MaskRCNNPredictor
from training.train_mask_rcnn import CocoPolygonMaskDataset, collate_fn, validate_data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the trained Mask R-CNN on the original validation split")
    parser.add_argument("--images", type=Path, default=PROJECT_DIR / "images")
    parser.add_argument("--annotations", type=Path, default=PROJECT_DIR / "merged_annotations.json")
    parser.add_argument("--model", type=Path, default=PROJECT_DIR / "output/mask_rcnn/mask_rcnn_state_dict.pt")
    parser.add_argument("--metadata", type=Path, default=PROJECT_DIR / "output/mask_rcnn/model_metadata.json")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--val-fraction", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--score-threshold", type=float, default=0.5)
    parser.add_argument("--mask-threshold", type=float, default=0.5)
    parser.add_argument("--match-iou", type=float, default=0.5)
    return parser.parse_args()


def encode_mask(mask: np.ndarray) -> dict:
    rle = mask_utils.encode(np.asfortranarray(mask.astype(np.uint8)))
    rle["counts"] = rle["counts"].decode("ascii")
    return rle


def mask_iou(left: np.ndarray, right: np.ndarray) -> float:
    intersection = np.logical_and(left, right).sum()
    union = np.logical_or(left, right).sum()
    return float(intersection / union) if union else 0.0


def update_counts(
    counts: dict[int, dict[str, int]],
    pred_masks: np.ndarray,
    pred_labels: np.ndarray,
    pred_scores: np.ndarray,
    gt_masks: np.ndarray,
    gt_labels: np.ndarray,
    category_ids: list[int],
    score_threshold: float,
    match_iou: float,
) -> None:
    for category_id in category_ids:
        prediction_indices = np.where(
            (pred_labels == category_id) & (pred_scores >= score_threshold)
        )[0]
        prediction_indices = prediction_indices[np.argsort(-pred_scores[prediction_indices])]
        ground_truth_indices = np.where(gt_labels == category_id)[0]
        unmatched = set(ground_truth_indices.tolist())
        for prediction_index in prediction_indices:
            best_index = None
            best_iou = 0.0
            for ground_truth_index in unmatched:
                current_iou = mask_iou(pred_masks[prediction_index], gt_masks[ground_truth_index])
                if current_iou > best_iou:
                    best_iou = current_iou
                    best_index = ground_truth_index
            if best_index is not None and best_iou >= match_iou:
                counts[category_id]["tp"] += 1
                unmatched.remove(best_index)
            else:
                counts[category_id]["fp"] += 1
        counts[category_id]["fn"] += len(unmatched)


def safe_ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def main() -> None:
    args = parse_args()
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    data, image_ids = validate_data(args.annotations, args.images)
    random.Random(args.seed).shuffle(image_ids)
    validation_count = max(1, round(len(image_ids) * args.val_fraction))
    validation_ids = image_ids[:validation_count]
    dataset = CocoPolygonMaskDataset(args.images, args.annotations, validation_ids, augment=False)
    loader = DataLoader(dataset, batch_size=1, shuffle=False, num_workers=0, collate_fn=collate_fn)
    predictor = MaskRCNNPredictor(str(args.model), str(args.metadata), args.device)

    category_ids = [category["id"] for category in data["categories"]]
    category_names = [category["name"] for category in data["categories"]]
    label_to_category = {
        int(label): int(category_id) for category_id, label in metadata["cat_to_label"].items()
    }
    detections: list[dict] = []
    counts = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})

    for images, targets in tqdm(loader, desc="validation inference"):
        image = images[0].to(predictor.device)
        target = targets[0]
        with torch.inference_mode():
            prediction = predictor.model([image])[0]
        boxes = prediction["boxes"].detach().cpu().numpy()
        labels = prediction["labels"].detach().cpu().numpy()
        scores = prediction["scores"].detach().cpu().numpy()
        masks = prediction["masks"].detach().cpu().numpy()[:, 0] >= args.mask_threshold
        image_id = int(target["image_id"].item())

        category_labels = np.array([label_to_category[int(label)] for label in labels], dtype=np.int64)
        for box, category_id, score, mask in zip(boxes, category_labels, scores, masks):
            x1, y1, x2, y2 = box.tolist()
            detections.append({
                "image_id": image_id,
                "category_id": int(category_id),
                "segmentation": encode_mask(mask),
                "bbox": [x1, y1, x2 - x1, y2 - y1],
                "score": float(score),
            })

        update_counts(
            counts,
            masks,
            category_labels,
            scores,
            target["masks"].numpy().astype(bool),
            np.array([label_to_category[int(label)] for label in target["labels"].numpy()]),
            category_ids,
            args.score_threshold,
            args.match_iou,
        )

    coco_ground_truth = COCO()
    coco_ground_truth.dataset = data
    coco_ground_truth.createIndex()
    coco_detections = coco_ground_truth.loadRes(detections)
    evaluator = COCOeval(coco_ground_truth, coco_detections, "segm")
    evaluator.params.imgIds = validation_ids
    evaluator.params.catIds = category_ids
    evaluator.evaluate()
    evaluator.accumulate()
    evaluator.summarize()

    precision = evaluator.eval["precision"]
    iou_50_index = int(np.where(np.isclose(evaluator.params.iouThrs, 0.5))[0][0])
    per_class_map50: list[float] = []
    per_class_map: list[float] = []
    for class_index in range(len(category_ids)):
        values_50 = precision[iou_50_index, :, class_index, 0, -1]
        values_all = precision[:, :, class_index, 0, -1]
        per_class_map50.append(float(values_50[values_50 > -1].mean()))
        per_class_map.append(float(values_all[values_all > -1].mean()))

    total_tp = sum(counts[category]["tp"] for category in category_ids)
    total_fp = sum(counts[category]["fp"] for category in category_ids)
    total_fn = sum(counts[category]["fn"] for category in category_ids)
    class_precision = [
        safe_ratio(counts[category]["tp"], counts[category]["tp"] + counts[category]["fp"])
        for category in category_ids
    ]
    class_recall = [
        safe_ratio(counts[category]["tp"], counts[category]["tp"] + counts[category]["fn"])
        for category in category_ids
    ]

    print("\n===== Mask R-CNN Validation Result =====")
    print(f"validation images : {len(validation_ids)}")
    print(f"score threshold   : {args.score_threshold:.2f}")
    print(f"mask IoU match    : {args.match_iou:.2f}")
    print(f"mask precision    : {safe_ratio(total_tp, total_tp + total_fp):.6f}")
    print(f"mask recall       : {safe_ratio(total_tp, total_tp + total_fn):.6f}")
    print(f"mask mAP50        : {evaluator.stats[1]:.6f}")
    print(f"mask mAP50-95     : {evaluator.stats[0]:.6f}")
    print(f"classes           : {category_names}")
    print(f"class precision   : {np.array(class_precision)}")
    print(f"class recall      : {np.array(class_recall)}")
    print(f"class mAP50       : {np.array(per_class_map50)}")
    print(f"class mAP50-95    : {np.array(per_class_map)}")


if __name__ == "__main__":
    main()
