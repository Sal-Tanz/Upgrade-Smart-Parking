"""
Evaluation Script untuk ML Pipeline.

Mengukur:
1. Plate Detection Accuracy (mAP, precision, recall)
2. OCR Accuracy (character-level dan full-plate)
3. Slot Classification Accuracy

Target Plan:
- Plate Detection mAP ≥ 0.90 pada IoU 0.5
- End-to-end ALPR accuracy ≥ 85%
- Slot Classification accuracy ≥ 90%
"""

import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

import numpy as np
from loguru import logger


@dataclass
class EvaluationMetrics:
    """Container untuk evaluation metrics."""
    model_name: str = ""
    total_samples: int = 0
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0

    # Timing
    avg_inference_time_ms: float = 0.0
    total_inference_time_ms: float = 0.0

    # Per-class metrics
    per_class: Dict[str, dict] = field(default_factory=dict)

    # For OCR
    char_accuracy: float = 0.0
    full_plate_accuracy: float = 0.0

    # Target comparison
    target_met: bool = False

    def format_table(self) -> str:
        """Format metrics as table."""
        lines = []
        lines.append(f"\n{'='*60}")
        lines.append(f"📊 Evaluation: {self.model_name}")
        lines.append(f"{'='*60}")
        lines.append(f"  Samples:            {self.total_samples}")
        lines.append(f"  Accuracy:           {self.accuracy:.2%}")
        lines.append(f"  Precision:          {self.precision:.2%}")
        lines.append(f"  Recall:             {self.recall:.2%}")
        lines.append(f"  F1 Score:           {self.f1_score:.2%}")
        lines.append(f"  Avg Inference:      {self.avg_inference_time_ms:.2f} ms")
        lines.append(f"  Target Met:         {'✅ YES' if self.target_met else '❌ NO'}")
        lines.append(f"{'='*60}")
        return "\n".join(lines)


def evaluate_plate_detector(
    model_path: str,
    test_images_dir: Optional[str] = None,
    ground_truth_file: Optional[str] = None,
    iou_threshold: float = 0.5,
    confidence_threshold: float = 0.5,
    target_map: float = 0.90
) -> EvaluationMetrics:
    """
    Evaluate plate detection model (YOLOv8).

    Args:
        model_path: Path ke trained model (.pt atau .onnx)
        test_images_dir: Directory test images
        ground_truth_file: File ground truth annotations
        iou_threshold: IoU threshold untuk positive detection
        confidence_threshold: Confidence threshold
        target_map: Target mAP (0.90 untuk YOLOv8)

    Returns:
        EvaluationMetrics
    """

    metrics = EvaluationMetrics(
        model_name="Plate Detector (YOLOv8)",
        total_samples=0
    )

    try:
        from ultralytics import YOLO

        logger.info(f"Evaluating plate detector: {model_path}")

        model = YOLO(model_path)

        if test_images_dir and Path(test_images_dir).exists():
            # Run validation on test set
            start_time = time.time()
            results = model.val(
                data=str(test_images_dir),
                imgsz=640,
                iou=iou_threshold,
                conf=confidence_threshold
            )
            inference_time = time.time() - start_time

            metrics.mAP50 = float(results.box.map50) if hasattr(results.box, 'map50') else 0.0
            metrics.mAP50_95 = float(results.box.map) if hasattr(results.box, 'map') else 0.0
            metrics.precision = float(results.box.mp) if hasattr(results.box, 'mp') else 0.0
            metrics.recall = float(results.box.mr) if hasattr(results.box, 'mr') else 0.0
            metrics.accuracy = metrics.mAP50

            metrics.target_met = metrics.mAP50 >= target_map

        else:
            logger.warning("No test data available for evaluation")
            logger.info("To evaluate, provide test_images_dir with YOLO-format labels")

    except ImportError:
        logger.warning("Ultralytics not installed. Run: pip install ultralytics")
    except Exception as e:
        logger.error(f"Error evaluating plate detector: {e}")

    return metrics


def evaluate_ocr_accuracy(
    predictions: List[str],
    ground_truth: List[str],
    target_accuracy: float = 0.85
) -> EvaluationMetrics:
    """
    Evaluate OCR end-to-end accuracy.

    Args:
        predictions: List of predicted plate texts
        ground_truth: List of ground truth plate texts
        target_accuracy: Target end-to-end accuracy (0.85)

    Returns:
        EvaluationMetrics
    """
    metrics = EvaluationMetrics(
        model_name="OCR (PaddleOCR/EasyOCR)",
        total_samples=len(ground_truth)
    )

    if len(predictions) != len(ground_truth):
        logger.error("Predictions and ground truth must have same length")
        return metrics

    # Character-level accuracy
    total_chars = 0
    correct_chars = 0

    # Full-plate accuracy
    correct_plates = 0

    for pred, gt in zip(predictions, ground_truth):
        pred_norm = pred.strip().upper().replace(" ", "")
        gt_norm = gt.strip().upper().replace(" ", "")

        # Character-level comparison using sequence alignment to avoid positional shift penalties
        from difflib import SequenceMatcher
        matcher = SequenceMatcher(None, pred_norm, gt_norm)
        matches = sum(triple.size for triple in matcher.get_matching_blocks())
        correct_chars += matches
        total_chars += max(len(pred_norm), len(gt_norm))

        # Full-plate match
        if pred_norm == gt_norm:
            correct_plates += 1

    if total_chars > 0:
        metrics.char_accuracy = correct_chars / total_chars

    if len(ground_truth) > 0:
        metrics.full_plate_accuracy = correct_plates / len(ground_truth)

    metrics.accuracy = metrics.full_plate_accuracy
    metrics.target_met = metrics.accuracy >= target_accuracy

    return metrics


def evaluate_slot_classifier(
    model_path: str,
    test_data_dir: Optional[str] = None,
    target_accuracy: float = 0.90
) -> EvaluationMetrics:
    """
    Evaluate slot classification model.

    Args:
        model_path: Path ke trained model (.pth atau .onnx)
        test_data_dir: Directory test data (ImageFolder format)
        target_accuracy: Target accuracy (0.90)

    Returns:
        EvaluationMetrics
    """
    metrics = EvaluationMetrics(
        model_name="Slot Classifier (MobileNetV3)",
        total_samples=0
    )

    try:
        import torch
        from torch.utils.data import DataLoader

        logger.info(f"Evaluating slot classifier: {model_path}")

        if test_data_dir and Path(test_data_dir).exists():
            from ml.training.train_slot import ParkingSlotDataset, get_augmentation

            # Load test data
            test_dataset = ParkingSlotDataset(
                test_data_dir,
                split="test",
                transform=get_augmentation(train=False)
            )
            test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)

            # Load model
            from ml.training.train_slot import create_mobilenetv3

            device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
            model = create_mobilenetv3()
            model.load_state_dict(torch.load(model_path, map_location=device))
            model.to(device)
            model.eval()

            # Evaluate
            correct = 0
            total = 0
            inference_times = []

            with torch.no_grad():
                for images, labels in test_loader:
                    images = images.to(device)
                    labels = labels.to(device)

                    start = time.time()
                    outputs = model(images)
                    inference_time = (time.time() - start) * 1000  # ms
                    inference_times.append(inference_time)

                    _, predicted = torch.max(outputs, 1)
                    correct += (predicted == labels).sum().item()
                    total += labels.size(0)

            metrics.total_samples = total
            metrics.accuracy = correct / total if total > 0 else 0.0
            metrics.avg_inference_time_ms = np.mean(inference_times) if inference_times else 0.0
            metrics.target_met = metrics.accuracy >= target_accuracy

        else:
            logger.warning("No test data available")
            logger.info("To evaluate, provide test_data_dir with ImageFolder structure")

    except ImportError:
        logger.warning("PyTorch not installed. Run: pip install torch")
    except Exception as e:
        logger.error(f"Error evaluating slot classifier: {e}")

    return metrics


def run_full_evaluation() -> Dict[str, EvaluationMetrics]:
    """
    Run full evaluation on all ML models.

    Returns:
        Dictionary dengan metrics untuk setiap model
    """
    logger.info("=" * 60)
    logger.info("Full ML Pipeline Evaluation")
    logger.info("=" * 60)

    results = {}

    # 1. Plate Detector
    plate_model = "ml/models/best.pt"
    if Path(plate_model).exists():
        results["plate_detector"] = evaluate_plate_detector(plate_model)
        logger.info(results["plate_detector"].format_table())
    else:
        logger.warning(f"Plate detector model not found: {plate_model}")

    # 2. OCR
    logger.info("OCR evaluation requires predictions and ground truth data")
    logger.info("Use evaluate_ocr_accuracy(predictions, ground_truth) directly")

    # 3. Slot Classifier
    slot_model = "ml/models/slot_classifier_best.pth"
    if Path(slot_model).exists():
        results["slot_classifier"] = evaluate_slot_classifier(slot_model)
        logger.info(results["slot_classifier"].format_table())
    else:
        logger.warning(f"Slot classifier model not found: {slot_model}")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate ML Pipeline")
    parser.add_argument("--full", action="store_true",
                        help="Run full evaluation")
    parser.add_argument("--plate-model", default="ml/models/best.pt",
                        help="Path to plate detector model")
    parser.add_argument("--slot-model", default="ml/models/slot_classifier_best.pth",
                        help="Path to slot classifier model")
    parser.add_argument("--ocr-predictions", default=None,
                        help="JSON file with OCR predictions")
    parser.add_argument("--ocr-ground-truth", default=None,
                        help="JSON file with ground truth")
    parser.add_argument("--target-map", type=float, default=0.90,
                        help="Target mAP for plate detection")
    parser.add_argument("--target-acc", type=float, default=0.90,
                        help="Target accuracy for slot classification")

    args = parser.parse_args()

    if args.full:
        results = run_full_evaluation()

        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("SUMMARY")
        logger.info("=" * 60)
        for name, metrics in results.items():
            status = "✅ PASS" if metrics.target_met else "❌ FAIL"
            logger.info(f"{name}: {status} (Accuracy: {metrics.accuracy:.2%})")

    else:
        # Individual evaluations
        if Path(args.plate_model).exists():
            metrics = evaluate_plate_detector(args.plate_model, target_map=args.target_map)
            print(metrics.format_table())

        if Path(args.slot_model).exists():
            metrics = evaluate_slot_classifier(args.slot_model, target_accuracy=args.target_acc)
            print(metrics.format_table())

        if args.ocr_predictions and args.ocr_ground_truth:
            import json
            with open(args.ocr_predictions) as f:
                predictions = json.load(f)
            with open(args.ocr_ground_truth) as f:
                ground_truth = json.load(f)
            metrics = evaluate_ocr_accuracy(predictions, ground_truth)
            print(metrics.format_table())