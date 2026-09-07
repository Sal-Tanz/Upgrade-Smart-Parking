"""
Training Script untuk Slot Classifier.

Menggunakan MobileNetV3-Small untuk klasifikasi slot parkir (kosong/terisi).

Architecture: MobileNetV3-Small (from torchvision)
Input: 224x224 RGB image
Output: 2 classes (empty, occupied)

See: https://pytorch.org/vision/stable/models/mobilenetv3.html
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms, models
from loguru import logger


class ParkingSlotDataset(Dataset):
    """Custom dataset for parking slot classification."""

    def __init__(
        self,
        root_dir: str,
        split: str = "train",
        transform=None
    ):
        """
        Args:
            root_dir: Directory dengan struktur {train,val,test}/class/
            split: 'train', 'val', atau 'test'
            transform: Optional transform untuk data augmentation
        """
        self.root_dir = Path(root_dir) / split
        self.transform = transform

        # Get all images
        self.samples = []
        for class_dir in self.root_dir.iterdir():
            if class_dir.is_dir():
                class_name = class_dir.name.lower()
                class_id = 0 if class_name in ["empty", "kosong", "available"] else 1

                for img_path in class_dir.glob("*.jpg"):
                    self.samples.append((img_path, class_id))
                for img_path in class_dir.glob("*.png"):
                    self.samples.append((img_path, class_id))

        logger.info(f"Loaded {len(self.samples)} samples for {split}")

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        from PIL import Image

        img_path, label = self.samples[idx]
        image = Image.open(img_path).convert("RGB")

        if self.transform:
            image = self.transform(image)

        return image, label


def get_augmentation(train: bool = True) -> transforms.Compose:
    """
    Get data augmentation pipeline.

    Args:
        train: Whether this is for training (includes augmentation)

    Returns:
        torchvision transform pipeline
    """
    if train:
        return transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.RandomResizedCrop(224, scale=(0.8, 1.0)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomRotation(degrees=10),
            transforms.ColorJitter(brightness=0.2, contrast=0.2),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
    else:
        return transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])


def create_mobilenetv3() -> nn.Module:
    """
    Create MobileNetV3-Small model untuk binary classification.

    Returns:
        Modified MobileNetV3 model dengan 2 output classes
    """
    model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)

    # Replace classifier
    model.classifier[-1] = nn.Linear(
        in_features=model.classifier[-1].in_features,
        out_features=2  # empty, occupied
    )

    return model


def train_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    optimizer: optim.Optimizer,
    device: torch.device
) -> Tuple[float, float]:
    model.train()
    total_loss = 0.0
    correct = 0
    total = 0

    for images, labels in dataloader:
        images = images.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        total_loss += loss.item()
        _, predicted = torch.max(outputs, 1)
        correct += (predicted == labels).sum().item()
        total += labels.size(0)

    avg_loss = total_loss / len(dataloader)
    accuracy = correct / total

    return avg_loss, accuracy


def validate(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    device: torch.device
) -> Tuple[float, float]:
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0

    with torch.no_grad():
        for images, labels in dataloader:
            images = images.to(device)
            labels = labels.to(device)

            outputs = model(images)
            loss = criterion(outputs, labels)

            total_loss += loss.item()
            _, predicted = torch.max(outputs, 1)
            correct += (predicted == labels).sum().item()
            total += labels.size(0)

    avg_loss = total_loss / len(dataloader)
    accuracy = correct / total

    return avg_loss, accuracy


def train_slot_classifier(
    data_dir: str = "ml/data/parking_slots",
    output_dir: str = "ml/models/",
    epochs: int = 50,
    batch_size: int = 32,
    learning_rate: float = 0.001,
    device: str = "cpu",
    patience: int = 10
) -> str:
    """
    Train MobileNetV3 untuk slot classification.

    Args:
        data_dir: Root directory dataset
        output_dir: Directory untuk menyimpan model
        epochs: Jumlah epochs training
        batch_size: Batch size
        learning_rate: Learning rate
        device: Device untuk training ("cpu", "cuda:0", "mps")
        patience: Early stopping patience

    Returns:
        Path ke model terbaik
    """
    logger.info("=" * 60)
    logger.info("Slot Classifier Training Pipeline")
    logger.info("=" * 60)

    device = torch.device(device if torch.cuda.is_available() else "cpu")
    logger.info(f"Device: {device}")

    # Setup data
    data_path = Path(data_dir)

    # Buat dataset placeholder jika tidak ada
    if not data_path.exists():
        data_path.mkdir(parents=True, exist_ok=True)
        for split in ['train', 'val', 'test']:
            for cls in ['empty', 'occupied']:
                (data_path / split / cls).mkdir(parents=True, exist_ok=True)
        logger.warning(f"Dataset directory created at {data_dir}. Add images to start training.")

    # Datasets
    train_dataset = ParkingSlotDataset(
        data_dir, split="train", transform=get_augmentation(train=True)
    )
    val_dataset = ParkingSlotDataset(
        data_dir, split="val", transform=get_augmentation(train=False)
    )

    if len(train_dataset) == 0:
        logger.error("No training data found. Add images to ml/data/parking_slots/train/")
        return ""

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=4)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=4)

    # Model
    model = create_mobilenetv3().to(device)
    logger.info(f"Model: MobileNetV3-Small ({sum(p.numel() for p in model.parameters()):,} params)")

    # Training
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", patience=3, factor=0.5)

    best_val_acc = 0.0
    best_epoch = 0
    epochs_without_improvement = 0

    for epoch in range(epochs):
        train_loss, train_acc = train_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_acc = validate(model, val_loader, criterion, device)

        scheduler.step(val_loss)

        logger.info(
            f"Epoch {epoch + 1}/{epochs} | "
            f"Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.2%} | "
            f"Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.2%}"
        )

        # Save best model
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_epoch = epoch + 1
            epochs_without_improvement = 0

            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            torch.save(model.state_dict(), output_path / "slot_classifier_best.pth")
            logger.success(f"New best model saved (Val Acc: {val_acc:.2%})")
        else:
            epochs_without_improvement += 1

        # Early stopping
        if epochs_without_improvement >= patience:
            logger.warning(f"Early stopping at epoch {epoch + 1} (no improvement for {patience} epochs)")
            break

    logger.success(f"Training complete! Best Val Acc: {best_val_acc:.2%} at epoch {best_epoch}")

    best_model_path = str(output_path / "slot_classifier_best.pth")
    return best_model_path


def export_to_onnx(
    model_path: str,
    output_path: str = "ml/models/slot_classifier.onnx",
    input_size: int = 224
) -> str:
    """
    Export PyTorch model ke ONNX format.

    Args:
        model_path: Path ke PyTorch model (.pth)
        output_path: Output path untuk ONNX model
        input_size: Input image size

    Returns:
        Path ke ONNX model
    """
    logger.info(f"Exporting {model_path} to ONNX...")

    device = torch.device("cpu")
    model = create_mobilenetv3()
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.to(device)
    model.eval()

    # Dummy input
    dummy_input = torch.randn(1, 3, input_size, input_size).to(device)

    # Export
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        export_params=True,
        opset_version=12,
        do_constant_folding=True,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={"input": {0: "batch_size"}, "output": {0: "batch_size"}}
    )

    logger.success(f"ONNX model exported to: {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Slot Classifier")

    parser.add_argument("--data", default="ml/data/parking_slots",
                        help="Path to dataset directory")
    parser.add_argument("--epochs", type=int, default=50,
                        help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=32,
                        help="Batch size")
    parser.add_argument("--device", default="cpu",
                        help="Device to train on")
    parser.add_argument("--export", action="store_true",
                        help="Export to ONNX after training")

    args = parser.parse_args()

    # Train
    model_path = train_slot_classifier(
        data_dir=args.data,
        epochs=args.epochs,
        batch_size=args.batch_size,
        device=args.device
    )

    # Export to ONNX
    if args.export:
        export_to_onnx(model_path)