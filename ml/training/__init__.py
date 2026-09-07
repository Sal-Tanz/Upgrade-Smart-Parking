"""
Training Module untuk Smart Parking System.

Modul ini berisi:
- data_prep.py: Data preparation dan augmentation utilities
- train_alpr.py: Training script untuk plate detector (YOLOv8)
- train_slot.py: Training script untuk slot classifier (MobileNetV3)
- evaluate.py: Evaluation script untuk mengukur akurasi model
"""

from ml.training.data_prep import (
    split_dataset,
    augment_image,
    create_yolo_dataset_yaml,
    prepare_slot_classification_dataset
)

from ml.training.train_alpr import (
    train_alpr,
    export_model,
    evaluate_model
)

from ml.training.train_slot import (
    train_slot_classifier,
    create_mobilenetv3
)

from ml.training.evaluate import (
    evaluate_plate_detector,
    evaluate_slot_classifier,
    evaluate_ocr_accuracy,
    run_full_evaluation
)

__all__ = [
    # Data preparation
    'split_dataset',
    'augment_image',
    'create_yolo_dataset_yaml',
    'prepare_slot_classification_dataset',

    # Training
    'train_alpr',
    'train_slot_classifier',
    'create_mobilenetv3',

    # Export
    'export_model',

    # Evaluation
    'evaluate_model',
    'evaluate_plate_detector',
    'evaluate_slot_classifier',
    'evaluate_ocr_accuracy',
    'run_full_evaluation',
]