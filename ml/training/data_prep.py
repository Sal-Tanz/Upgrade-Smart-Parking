"""
Data Preparation Utilities untuk Training Pipeline.

Fungsi:
- Convert dataset ke format YOLO (YOLOv8)
- Convert dataset ke format ImageFolder (MobileNetV3)
- Data augmentation (rotasi ±15°, lighting variation, blur, noise)
- Train/val/test split (80/10/10)
"""

import os
import shutil
import random
from pathlib import Path
from typing import List, Dict, Tuple
import json
import cv2
import numpy as np
from loguru import logger


def split_dataset(
    source_dir: str,
    output_dir: str,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    seed: int = 42
) -> None:
    """
    Split dataset menjadi train/val/test sets.

    Args:
        source_dir: Directory berisi semua data (images dan labels)
        output_dir: Directory output untuk train/val/test
        train_ratio: Ratio untuk training set (default 0.8)
        val_ratio: Ratio untuk validation set (default 0.1)
        test_ratio: Ratio untuk test set (default 0.1)
        seed: Random seed untuk reproducibility
    """
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, \
        "Ratios must sum to 1.0"

    random.seed(seed)

    # Create output directories
    for split in ['train', 'val', 'test']:
        Path(output_dir) / split / 'images' / 'plates'
        Path(output_dir) / split / 'labels'

    # Get all image files
    images_dir = Path(source_dir) / 'images' / 'plates'
    if not images_dir.exists():
        raise FileNotFoundError(f"Images directory not found: {images_dir}")

    image_files = list(images_dir.glob('*.jpg')) + list(images_dir.glob('*.png'))
    if not image_files:
        raise FileNotFoundError(f"No images found in {images_dir}")

    # Shuffle
    random.shuffle(image_files)

    # Calculate split indices
    n = len(image_files)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)

    splits = {
        'train': image_files[:n_train],
        'val': image_files[n_train:n_train + n_val],
        'test': image_files[n_train + n_val:]
    }

    # Copy files
    labels_dir = Path(source_dir) / 'labels'
    for split_name, split_files in splits.items():
        logger.info(f"Processing {split_name}: {len(split_files)} files")

        for img_path in split_files:
            # Copy image
            dst_img = Path(output_dir) / split_name / 'images' / 'plates' / img_path.name
            dst_img.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(img_path, dst_img)

            # Copy label if exists
            label_name = img_path.stem + '.txt'
            label_path = labels_dir / label_name
            if label_path.exists():
                dst_label = Path(output_dir) / split_name / 'labels' / label_name
                dst_label.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(label_path, dst_label)

    logger.info(f"Dataset split complete: {output_dir}")
    logger.info(f"  Train: {len(splits['train'])} samples")
    logger.info(f"  Val: {len(splits['val'])} samples")
    logger.info(f"  Test: {len(splits['test'])} samples")


def augment_image(
    image: np.ndarray,
    rotation_range: float = 15.0,
    brightness_range: Tuple[float, float] = (0.7, 1.3),
    add_blur: bool = False,
    add_noise: bool = False
) -> np.ndarray:
    """
    Apply data augmentation ke image.

    Args:
        image: Input image (BGR format)
        rotation_range: Maximum rotation angle in degrees (±)
        brightness_range: Brightness multiplier range (min, max)
        add_blur: Whether to add Gaussian blur
        add_noise: Whether to add Gaussian noise

    Returns:
        Augmented image
    """
    h, w = image.shape[:2]

    # Rotation
    if rotation_range > 0:
        angle = random.uniform(-rotation_range, rotation_range)
        center = (w / 2, h / 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        image = cv2.warpAffine(image, rotation_matrix, (w, h))

    # Brightness variation
    brightness = random.uniform(brightness_range[0], brightness_range[1])
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 2] = np.clip(hsv[:, :, 2] * brightness, 0, 255)
    image = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    # Gaussian blur
    if add_blur:
        kernel_size = random.choice([3, 5])
        image = cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)

    # Gaussian noise
    if add_noise:
        noise = np.random.normal(0, 25, image.shape).astype(np.uint8)
        image = cv2.add(image, noise)

    return image


def convert_to_yolo_format(
    annotations: List[Dict],
    image_width: int,
    image_height: int,
    output_path: str
) -> None:
    """
    Convert annotations ke YOLO format (class_id, x_center, y_center, width, height).

    Args:
        annotations: List of bounding box annotations
            Each annotation: {'class_id': int, 'bbox': [x1, y1, x2, y2]}
        image_width: Width of the image in pixels
        image_height: Height of the image in pixels
        output_path: Output path for YOLO label file (.txt)
    """
    with open(output_path, 'w') as f:
        for ann in annotations:
            class_id = ann['class_id']
            x1, y1, x2, y2 = ann['bbox']

            # Convert to YOLO format (normalized center coordinates)
            x_center = ((x1 + x2) / 2.0) / image_width
            y_center = ((y1 + y2) / 2.0) / image_height
            width = (x2 - x1) / image_width
            height = (y2 - y1) / image_height

            # Write to file
            f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")


def create_yolo_dataset_yaml(
    dataset_dir: str,
    output_path: str,
    class_names: List[str] = None
) -> None:
    """
    Create YOLO dataset configuration YAML file.

    Args:
        dataset_dir: Root directory of the dataset
        output_path: Output path for YAML file
        class_names: List of class names (default: ['plate'])
    """
    if class_names is None:
        class_names = ['plate']

    yaml_content = f"""# YOLO Dataset Configuration
path: {dataset_dir}
train: train/images/plates
val: val/images/plates
test: test/images/plates

names:
"""

    for i, name in enumerate(class_names):
        yaml_content += f"  {i}: {name}\n"

    with open(output_path, 'w') as f:
        f.write(yaml_content)

    logger.info(f"YOLO dataset YAML created: {output_path}")


def prepare_slot_classification_dataset(
    source_dir: str,
    output_dir: str,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    seed: int = 42
) -> None:
    """
    Prepare dataset untuk slot classification (ImageFolder format).

    Expected source structure:
        source_dir/
            occupied/
                img1.jpg
                img2.jpg
            empty/
                img3.jpg
                img4.jpg

    Output structure:
        output_dir/
            train/
                occupied/
                empty/
            val/
                occupied/
                empty/
            test/
                occupied/
                empty/
    """
    random.seed(seed)

    # Get class directories
    class_dirs = [d for d in Path(source_dir).iterdir() if d.is_dir()]

    for split in ['train', 'val', 'test']:
        for class_dir in class_dirs:
            (Path(output_dir) / split / class_dir.name).mkdir(parents=True, exist_ok=True)

    # Process each class
    for class_dir in class_dirs:
        images = list(class_dir.glob('*.jpg')) + list(class_dir.glob('*.png'))
        random.shuffle(images)

        n = len(images)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)

        splits = {
            'train': images[:n_train],
            'val': images[n_train:n_train + n_val],
            'test': images[n_train + n_val:]
        }

        for split_name, split_files in splits.items():
            for img_path in split_files:
                dst = Path(output_dir) / split_name / class_dir.name / img_path.name
                shutil.copy2(img_path, dst)

        logger.info(f"{class_dir.name}: {n} total, {n_train} train, {n_val} val, {len(splits['test'])} test")


if __name__ == "__main__":
    # Example usage
    logger.info("Data preparation utilities loaded successfully")
    logger.info("Use split_dataset() to prepare YOLO dataset")
    logger.info("Use prepare_slot_classification_dataset() for MobileNetV3 dataset")
