"""
Modul ALPR (Automatic License Plate Recognition).

Pipeline:
    1. detector.py  - Lokalisasi plat nomor menggunakan YOLOv8
    2. preprocessor.py - Preprocessing gambar sebelum OCR
    3. ocr.py       - OCR menggunakan PaddleOCR/EasyOCR
    4. pipeline.py  - End-to-end ALPR pipeline

Usage:
    from ml.alpr.pipeline import ALPRPipeline
    alpr = ALPRPipeline()
    result = alpr.process("image.jpg")
"""

from ml.alpr.pipeline import ALPRPipeline
from ml.alpr.detector import PlateDetector
from ml.alpr.ocr import PlateOCR
from ml.alpr.preprocessor import PlatePreprocessor

__all__ = [
    "ALPRPipeline",
    "PlateDetector",
    "PlateOCR",
    "PlatePreprocessor",
]