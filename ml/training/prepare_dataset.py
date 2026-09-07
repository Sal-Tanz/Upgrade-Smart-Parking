"""
Persiapan Dataset untuk Training YOLOv8 Plate Detector.

Fungsi:
- Copy dataset images ke struktur YOLO (train/val/test split 80/10/10)
- Buat data.yaml configuration
- Siapkan direktori labels (kosong, siap untuk annotasi)

Penggunaan:
    python -m ml.training.prepare_dataset
    python -m ml.training.prepare_dataset --source image/data_set --output ml/data/license_plates
"""

import argparse
import random
import shutil
from pathlib import Path

import cv2
import numpy as np
from loguru import logger


def split_dataset(
    source_dir: str = "image/data_set",
    output_dir: str = "ml/data/license_plates",
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    seed: int = 42,
) -> dict:
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, \
        "Ratios must sum to 1.0"

    random.seed(seed)

    # Collect all image files
    source_path = Path(source_dir)
    image_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    image_files = sorted(
        [f for f in source_path.iterdir() if f.suffix.lower() in image_exts]
    )

    if not image_files:
        logger.error(f"Tidak ada gambar ditemukan di {source_dir}")
        return {}

    logger.info(f"Ditemukan {len(image_files)} gambar di {source_dir}")

    # Shuffle
    random.shuffle(image_files)

    # Split indices
    n = len(image_files)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)

    splits = {
        'train': image_files[:n_train],
        'val': image_files[n_train:n_train + n_val],
        'test': image_files[n_train + n_val:],
    }

    # Create output directories and copy files
    output_path = Path(output_dir)
    split_counts = {}

    for split_name, split_files in splits.items():
        img_dir = output_path / split_name / 'images' / 'plates'
        label_dir = output_path / split_name / 'labels'

        img_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)

        count = 0
        for img_path in split_files:
            dst_img = img_dir / img_path.name
            shutil.copy2(img_path, dst_img)

            # Create empty label file if none exists
            label_name = img_path.stem + '.txt'
            label_path = label_dir / label_name
            if not label_path.exists():
                label_path.touch()

            count += 1

        split_counts[split_name] = count
        logger.info(f"  {split_name}: {count} images -> {img_dir}")

    return split_counts


def create_data_yaml(
    output_dir: str = "ml/data/license_plates",
    class_names: list[str] = None,
) -> str:
    if class_names is None:
        class_names = ['plate']

    output_path = Path(output_dir)
    abs_path = str(output_path.resolve())

    yaml_lines = [
        f"path: {abs_path}",
        "train: train/images/plates",
        "val: val/images/plates",
        "test: test/images/plates",
        "",
        "names:",
    ]
    for i, name in enumerate(class_names):
        yaml_lines.append(f"  {i}: {name}")

    yaml_content = "\n".join(yaml_lines) + "\n"

    yaml_file = output_path / "data.yaml"
    yaml_file.write_text(yaml_content)

    logger.success(f"Dataset YAML dibuat: {yaml_file}")
    return str(yaml_file)


def verify_dataset(output_dir: str = "ml/data/license_plates") -> bool:
    output_path = Path(output_dir)
    yaml_file = output_path / "data.yaml"

    if not yaml_file.exists():
        logger.error(f"data.yaml tidak ditemukan: {yaml_file}")
        return False

    logger.info(f"\n{'='*50}")
    logger.info("VERIFIKASI DATASET")
    logger.info(f"{'='*50}")

    total = 0
    for split in ['train', 'val', 'test']:
        img_dir = output_path / split / 'images' / 'plates'
        label_dir = output_path / split / 'labels'

        if not img_dir.exists():
            logger.warning(f"  {split}: direktori tidak ditemukan")
            continue

        images = sorted(img_dir.iterdir())
        labels = sorted(label_dir.iterdir()) if label_dir.exists() else []

        n_img = len(images)
        n_lbl = len(labels)
        total += n_img

        status = "✅" if n_img > 0 else "⚠️"
        logger.info(f"  {status} {split}: {n_img} images, {n_lbl} labels")

    if total == 0:
        logger.error("Dataset kosong!")
        return False

    # Show first few files
    logger.info(f"\nContoh file train:")
    train_dir = output_path / 'train' / 'images' / 'plates'
    if train_dir.exists():
        for f in sorted(train_dir.iterdir())[:5]:
            logger.info(f"  {f.name}")

    logger.success(f"\nDataset siap! Total: {total} images")
    logger.info(f"Config: {yaml_file}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Siapkan dataset untuk training YOLOv8")
    parser.add_argument("--source", default="image/data_set",
                        help="Direktori sumber gambar (default: image/data_set)")
    parser.add_argument("--output", default="ml/data/license_plates",
                        help="Direktori output dataset YOLO (default: ml/data/license_plates)")
    parser.add_argument("--train-ratio", type=float, default=0.8,
                        help="Rasio training set (default: 0.8)")
    parser.add_argument("--val-ratio", type=float, default=0.1,
                        help="Rasio validation set (default: 0.1)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (default: 42)")

    args = parser.parse_args()

    logger.info("=" * 50)
    logger.info("PERSIAPAN DATASET YOLOv8")
    logger.info("=" * 50)
    logger.info(f"Source: {args.source}")
    logger.info(f"Output: {args.output}")
    logger.info(f"Split: train={args.train_ratio:.0%}, "
                f"val={args.val_ratio:.0%}, test={1-args.train_ratio-args.val_ratio:.0%}")

    counts = split_dataset(
        source_dir=args.source,
        output_dir=args.output,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        seed=args.seed,
    )

    if counts:
        create_data_yaml(output_dir=args.output)
        verify_dataset(output_dir=args.output)

        logger.info(f"\n{'='*50}")
        logger.info("LANGKAH SELANJUTNYA")
        logger.info(f"{'='*50}")
        logger.info("1. Annotasi bounding box plat nomor di setiap gambar")
        logger.info("   Gunakan tools: labelImg, CVAT, Roboflow, atau Label Studio")
        logger.info("2. Format annotasi YOLO: <class_id> <x_center> <y_center> <width> <height>")
        logger.info("   Simpan di direktori labels/ dengan nama sesuai gambar (.txt)")
        logger.info(f"3. Jalankan training:\n"
                    f"   python -m ml.training.train_alpr --data {Path(args.output).resolve() / 'data.yaml'}")
