"""
Training Script untuk YOLOv8 Plate Detector.

Alur:
1. Load pretrained YOLOv8 model (yolov8n.pt)
2. Train pada dataset plat nomor Indonesia
3. Evaluate model performance
4. Export ke ONNX format

Target:
- mAP ≥ 0.90 pada IoU 0.5
- End-to-end ALPR accuracy ≥ 85%

See: https://docs.ultralytics.com/modes/train/
"""

import argparse
from pathlib import Path
from ultralytics import YOLO
from loguru import logger


def check_dataset(dataset_yaml: str) -> bool:
    """
    Verify dataset structure is correct before training.

    Args:
        dataset_yaml: Path to data.yaml configuration file

    Returns:
        True if dataset is valid, False otherwise
    """
    import yaml

    logger.info(f"Checking dataset: {dataset_yaml}")

    try:
        with open(dataset_yaml, 'r') as f:
            config = yaml.safe_load(f)

        # Check required keys
        required_keys = ['path', 'train', 'val', 'names']
        for key in required_keys:
            if key not in config:
                logger.error(f"Missing required key '{key}' in {dataset_yaml}")
                return False

        # Check paths exist
        dataset_path = Path(config['path'])
        if not dataset_path.exists():
            logger.error(f"Dataset path does not exist: {dataset_path}")
            return False

        train_path = dataset_path / config['train']
        val_path = dataset_path / config['val']

        if not train_path.exists():
            logger.error(f"Train path does not exist: {train_path}")
            return False

        if not val_path.exists():
            logger.warning(f"Val path does not exist: {val_path}")
            logger.warning("Setting val = train for validation")
            config['val'] = config['train']

        # Count images
        train_images = list(train_path.glob('*.jpg')) + list(train_path.glob('*.png'))
        logger.info(f"Train images: {len(train_images)}")

        if len(train_images) == 0:
            logger.error("No training images found!")
            return False

        logger.success(f"Dataset validated: {len(train_images)} training images, {len(config['names'])} classes")
        return True

    except Exception as e:
        logger.error(f"Error checking dataset: {e}")
        return False


def train_alpr(
    data_yaml: str = "ml/data/license_plates/data.yaml",
    model_name: str = "yolov8n.pt",
    epochs: int = 100,
    imgsz: int = 640,
    batch: int = 16,
    device: str = "cpu",
    workers: int = 8,
    patience: int = 50,
    output_dir: str = "ml/models/"
) -> str:
    """
    Train YOLOv8 model for license plate detection.

    Args:
        data_yaml: Path ke data.yaml dengan train/val/test configuration
        model_name: Nama model pretrained (yolov8n.pt atau yolov8s.pt)
        epochs: Jumlah epochs training
        imgsz: Ukuran input image
        batch: Batch size
        device: Device untuk training ("cpu", "cuda:0", "mps")
        workers: Jumlah data loader workers
        patience: Epochs to wait for improvement before early stopping
        output_dir: Directory untuk menyimpan hasil training

    Returns:
        Path ke model terbaik (best.pt)
    """
    logger.info("=" * 60)
    logger.info("ALPR Training Pipeline")
    logger.info("=" * 60)
    logger.info(f"Config: model={model_name}, epochs={epochs}, imgsz={imgsz}, batch={batch}")

    # Check dataset
    dataset_yaml = Path(data_yaml)
    if not dataset_yaml.exists():
        logger.error(f"Dataset YAML not found: {data_yaml}")
        logger.info("Creating placeholder dataset configuration...")

        # Create data directory
        data_dir = Path("ml/data/license_plates")
        data_dir.mkdir(parents=True, exist_ok=True)

        # Create dataset YAML
        yaml_content = f"""
path: {data_dir.absolute()}
train: train/images/plates
val: val/images/plates
test: test/images/plates

names:
  0: plate
"""
        dataset_yaml.parent.mkdir(parents=True, exist_ok=True)
        with open(dataset_yaml, 'w') as f:
            f.write(yaml_content)
        logger.info(f"Created dataset YAML at {dataset_yaml}")

    logger.info("Loading pretrained YOLOv8 model...")
    model = YOLO(model_name)

    logger.info(f"Starting training with {epochs} epochs...")
    results = model.train(
        data=str(dataset_yaml),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        workers=workers,
        patience=patience,
        name="alpr_plate_detector",
        exist_ok=True
    )

    logger.success("Training complete!")
    logger.info(f"Results: {results}")

    best_model_path = "ml/models/best.pt"
    best_model_path_export = Path("runs/detect/alpr_plate_detector/weights/best.pt")
    if best_model_path_export.exists():
        import shutil
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        shutil.copy(best_model_path_export, best_model_path)
        logger.success(f"Best model saved to: {best_model_path}")

    return best_model_path


def export_model(
    model_path: str = "ml/models/best.pt",
    output_path: str = "ml/models/yolov8_plate.onnx",
    imgsz: int = 640,
    opset: int = 12
) -> str:
    """
    Export model ke ONNX format untuk production inference.

    Args:
        model_path: Path ke trained model (.pt)
        output_path: Output path untuk ONNX model
        imgsz: Image size untuk export
        opset: ONNX opset version

    Returns:
        Path ke ONNX model
    """
    logger.info(f"Exporting model {model_path} to ONNX format...")

    model = YOLO(model_path)

    model.export(
        format="onnx",
        imgsz=imgsz,
        opset=opset,
        simplify=True,
        dynamic=False  # Fixed input size for deployment
    )

    # Move to output path
    onnx_path = Path(model_path).with_suffix('.onnx')
    if onnx_path.exists():
        import shutil
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(onnx_path, output_path)
        logger.success(f"ONNX model saved to: {output_path}")
    else:
        logger.error("ONNX export failed")

    return output_path


def evaluate_model(model_path: str, data_yaml: str) -> dict:
    """
    Evaluate model performance.

    Args:
        model_path: Path ke trained model
        data_yaml: Path ke dataset YAML

    Returns:
        Dictionary dengan metrics (mAP50, mAP50-95, precision, recall)
    """
    logger.info(f"Evaluating model: {model_path}")

    model = YOLO(model_path)
    metrics = model.val(data=data_yaml)

    results = {
        "mAP50": float(metrics.box.map50),
        "mAP50_95": float(metrics.box.map),
        "precision": float(metrics.box.mp),
        "recall": float(metrics.box.mr),
    }

    logger.info("Evaluation Results:")
    for key, value in results.items():
        logger.info(f"  {key}: {value:.4f}")

    # Check against target
    if results["mAP50"] >= 0.90:
        logger.success("✅ Target mAP achieved: {:.2f} >= 0.90".format(results["mAP50"]))
    else:
        logger.warning(
            f"⚠️  Target mAP not achieved: {results['mAP50']:.2f} < 0.90. "
            "Consider more training data or epochs."
        )

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train ALPR Plate Detector")

    parser.add_argument("--data", default="ml/data/license_plates/data.yaml",
                        help="Path to dataset YAML file")
    parser.add_argument("--model", default="yolov8n.pt",
                        help="Pretrained model name")
    parser.add_argument("--epochs", type=int, default=100,
                        help="Number of training epochs")
    parser.add_argument("--batch", type=int, default=16,
                        help="Batch size")
    parser.add_argument("--device", default="cpu",
                        help="Device to train on (cpu, cuda:0, mps)")
    parser.add_argument("--export", action="store_true",
                        help="Export to ONNX after training")
    parser.add_argument("--evaluate", action="store_true",
                        help="Evaluate model after training")

    args = parser.parse_args()

    # Train
    model_path = train_alpr(
        data_yaml=args.data,
        model_name=args.model,
        epochs=args.epochs,
        batch=args.batch,
        device=args.device
    )

    # Evaluate
    if args.evaluate:
        evaluate_model(model_path, args.data)

    # Export
    if args.export:
        export_model(model_path)