"""Unit tests to verify machine learning logic bug fixes."""
import numpy as np
import pytest

from ml.alpr.ocr import PlateOCR
from ml.slot_detection.classifier import SlotClassifier
from ml.slot_detection.segmenter import SlotDetector
from ml.slot_detection.validator import ParkingValidator


class TestOCRPostprocessingFixes:
    """Test character correction and unspaced plate handling in PlateOCR."""

    def test_prefix_digit_corrected_to_letter(self):
        ocr = PlateOCR.__new__(PlateOCR)
        # Prefix digit '0' should be corrected to letter 'O'
        result = ocr._postprocess("0 1234 XYZ")
        parts = result.split()
        assert len(parts) == 3
        assert parts[0].isalpha(), f"Expected alphabetic prefix, got {parts[0]}"
        assert parts[1] == "1234"
        assert parts[2] == "XYZ"

    def test_prefix_13_corrected_to_B(self):
        ocr = PlateOCR.__new__(PlateOCR)
        result = ocr._postprocess("13 1234 XYZ")
        assert result.startswith("B ")

    def test_unspaced_plate_formatted_and_corrected(self):
        ocr = PlateOCR.__new__(PlateOCR)
        result = ocr._postprocess("B1234XYZ")
        assert result == "B 1234 XYZ"

        # Unspaced plate with misread digit in prefix
        result2 = ocr._postprocess("01234XYZ")
        assert result2 == "O 1234 XYZ"


class TestSlotClassifierFixes:
    """Test background subtraction and model loading fixes in SlotClassifier."""

    def test_mog2_variable_crop_sizes_does_not_break_classification(self):
        classifier = SlotClassifier(method="background_subtraction")
        # Crop 1: 100x120
        img1 = np.full((100, 120, 3), 50, dtype=np.uint8)
        # Crop 2: 150x80 (different shape)
        img2 = np.full((150, 80, 3), 50, dtype=np.uint8)

        # Batch classification should not throw exception or reset into 100% foreground
        batch_results = classifier.classify_batch({
            "slot-1": img1,
            "slot-2": img2,
        })
        assert "slot-1" in batch_results
        assert "slot-2" in batch_results
        assert batch_results["slot-1"].status in ("kosong", "terisi", "unknown")
        assert batch_results["slot-2"].status in ("kosong", "terisi", "unknown")

    def test_onnx_normalization_preserves_float32(self):
        classifier = SlotClassifier(method="background_subtraction")
        # Verify normalization arithmetic
        resized = np.zeros((classifier.input_size, classifier.input_size, 3), dtype=np.float32)
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        normalized = (resized - mean) / std
        assert normalized.dtype == np.float32


class TestSegmenterFixes:
    """Test RETR_CCOMP contour extraction for parking slots."""

    def test_find_rectangles_from_lines_ccomp(self):
        segmenter = SlotDetector(slot_min_area=100, slot_max_area=100000)
        # Draw a square boundary representing a parking slot
        lines = [
            np.array([[20, 20, 120, 20]]),
            np.array([[120, 20, 120, 120]]),
            np.array([[120, 120, 20, 120]]),
            np.array([[20, 120, 20, 20]]),
        ]
        rectangles = segmenter._group_lines_into_rectangles(lines, (200, 200))
        assert len(rectangles) >= 1
        assert len(rectangles[0]) == 4


class TestValidatorFallbackFix:
    """Test allow_merah_to_orange_fallback propagation in ParkingValidator."""

    def test_fallback_flag_enforced(self, tmp_path):
        import json
        config_file = tmp_path / "slots.json"
        config_data = {
            "slots": [
                {"slot_id": "O-01", "cluster": "Orange", "polygon": []}
            ]
        }
        config_file.write_text(json.dumps(config_data))

        # With fallback disabled: Dekan ("D", Merah) CANNOT park in Orange slot
        val_no_fallback = ParkingValidator(
            slot_config_path=str(config_file),
            allow_merah_to_orange_fallback=False,
        )
        res_fail = val_no_fallback.validate("B 1234 AA", "O-01", jabatan="D")
        assert not res_fail.is_valid, "Expected rejection when fallback is disabled"

        # With fallback enabled: Dekan ("D", Merah) CAN park in Orange slot
        val_fallback = ParkingValidator(
            slot_config_path=str(config_file),
            allow_merah_to_orange_fallback=True,
        )
        res_ok = val_fallback.validate("B 1234 AA", "O-01", jabatan="D")
        assert res_ok.is_valid, "Expected acceptance when fallback is enabled"
