"""
Modul Slot Detection untuk Sistem Parkir Cerdas.

Pipeline:
    1. segmenter.py  - Deteksi garis parkir menggunakan Hough Line Transform
    2. classifier.py - Klasifikasi slot (kosong/terisi) menggunakan CNN
    3. validator.py  - Validasi posisi kendaraan di slot yang benar

Penggunaan:
    from ml.slot_detection import SlotDetector, SlotClassifier, ParkingValidator
    
    # Setup slot configuration
    detector = SlotDetector()
    slots = detector.detect_slots(image)
    
    # Classify slot status
    classifier = SlotClassifier()
    status = classifier.classify(slot_image)
    
    # Validate parking position
    validator = ParkingValidator(slot_config)
    is_valid = validator.validate(plate_text, slot_id)
"""

from ml.slot_detection.segmenter import SlotDetector
from ml.slot_detection.classifier import SlotClassifier
from ml.slot_detection.validator import ParkingValidator

__all__ = [
    "SlotDetector",
    "SlotClassifier",
    "ParkingValidator",
]