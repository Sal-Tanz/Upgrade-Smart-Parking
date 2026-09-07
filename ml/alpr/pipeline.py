"""
ALPR End-to-End Pipeline untuk Sistem Parkir Cerdas.

Pipeline lengkap dari gambar/frame kamera sampai teks plat nomor:
    1. Deteksi plat nomor (YOLOv8)
    2. Crop & preprocessing gambar plat
    3. OCR untuk membaca teks plat
    4. Post-processing & validasi format

Penggunaan:
    from ml.alpr.pipeline import ALPRPipeline
    
    alpr = ALPRPipeline()
    result = alpr.process("image.jpg")
    
    print(result.plate_text)      # "B 1234 XYZ"
    print(result.confidence)      # 0.92
    print(result.is_valid)        # True
    print(result.vehicle_status)  # "ACCEPTED" / "REJECTED"

Pipeline Flow:
    [Image/Frame] 
        → PlateDetector (YOLOv8) → bbox + cropped image
        → PlatePreprocessor → cleaned image
        → PlateOCR (PaddleOCR) → raw text
        → Post-processing → normalized text
        → Validation → final result
"""

from pathlib import Path
from typing import Optional, Union
from dataclasses import dataclass
from enum import Enum

import cv2
import numpy as np
from loguru import logger

from ml.alpr.detector import PlateDetector, PlateDetection
from ml.alpr.preprocessor import PlatePreprocessor
from ml.alpr.ocr import PlateOCR, OCRResult


class VehicleStatus(Enum):
    """Status kendaraan berdasarkan hasil ALPR."""
    ACCEPTED = "ACCEPTED"      # Plat terdeteksi dan valid format
    REJECTED = "REJECTED"      # Plat tidak terdeteksi atau invalid
    RETRY = "RETRY"            # Confidence terlalu rendah, perlu scan ulang


@dataclass
class ALPRResult:
    """Hasil akhir dari ALPR pipeline."""
    # Informasi plat
    plate_text: str                              # Teks plat nomor (normalized)
    raw_plate_text: str                          # Teks mentah dari OCR
    
    # Confidence scores
    detection_confidence: float                  # Confidence deteksi plat (YOLO)
    ocr_confidence: float                        # Confidence OCR
    overall_confidence: float                    # Confidence keseluruhan
    
    # Bounding box
    bbox: Optional[tuple[int, int, int, int]]    # x1, y1, x2, y2 (pixel)
    
    # Status & metadata
    vehicle_status: VehicleStatus                # ACCEPTED / REJECTED / RETRY
    is_valid_format: bool                        # Format plat Indonesia valid
    ocr_engine_used: str                         # Engine OCR yang dipakai
    
    # Images (optional, untuk debugging/visualisasi)
    original_image: Optional[np.ndarray] = None
    cropped_plate: Optional[np.ndarray] = None
    processed_plate: Optional[np.ndarray] = None
    annotated_image: Optional[np.ndarray] = None
    
    # Error message (jika ada)
    error_message: Optional[str] = None


class ALPRPipeline:
    """
    End-to-end ALPR pipeline.

    Args:
        detector_model_path: Path ke model YOLOv8 untuk deteksi plat
        ocr_engine: Engine OCR ("paddleocr" atau "easyocr")
        detection_confidence_threshold: Threshold confidence deteksi (default 0.5)
        ocr_confidence_threshold: Threshold confidence OCR (default 0.5)
        overall_confidence_threshold: Threshold confidence keseluruhan (default 0.6)
        device: Device inference ("cpu", "cuda", "mps")
        debug: Simpan intermediate images untuk debugging (default False)
    """

    def __init__(
        self,
        detector_model_path: str = "ml/models/yolov8_plate.pt",
        ocr_engine: str = "paddleocr",
        detection_confidence_threshold: float = 0.5,
        ocr_confidence_threshold: float = 0.5,
        overall_confidence_threshold: float = 0.6,
        device: str = "cpu",
        debug: bool = False,
    ):
        self.detection_conf_threshold = detection_confidence_threshold
        self.ocr_conf_threshold = ocr_confidence_threshold
        self.overall_conf_threshold = overall_confidence_threshold
        self.debug = debug

        # Initialize sub-modules
        logger.info("Initializing ALPR Pipeline...")
        
        self.detector = PlateDetector(
            model_path=detector_model_path,
            confidence_threshold=detection_confidence_threshold,
            device=device,
        )
        
        self.preprocessor = PlatePreprocessor(
            enable_deskew=True,
            enable_denoise=True,
            debug=debug,
        )
        
        self.ocr = PlateOCR(
            engine=ocr_engine,
            confidence_threshold=ocr_confidence_threshold,
        )

        logger.info(
            f"ALPR Pipeline siap | device={device} | "
            f"det_conf={detection_confidence_threshold} | "
            f"ocr_conf={ocr_confidence_threshold} | "
            f"overall_conf={overall_confidence_threshold}"
        )

    def process(
        self,
        image: Union[str, Path, np.ndarray],
        return_images: bool = False,
    ) -> ALPRResult:
        """
        Process gambar/frame kamera untuk mendeteksi dan membaca plat nomor.

        Args:
            image: Path ke file gambar atau numpy array (BGR dari OpenCV)
            return_images: Jika True, simpan intermediate images di result

        Returns:
            ALPRResult berisi teks plat, confidence, dan status
        """
        # Load image jika input adalah path
        if isinstance(image, (str, Path)):
            image_path = str(image)
            if not Path(image_path).exists():
                logger.error(f"File gambar tidak ditemukan: {image_path}")
                return self._create_error_result(f"File tidak ditemukan: {image_path}")
            
            original_image = cv2.imread(image_path)
            if original_image is None:
                logger.error(f"Gagal membaca gambar: {image_path}")
                return self._create_error_result(f"Gagal membaca gambar: {image_path}")
        else:
            original_image = image.copy()

        # Step 1: Deteksi plat nomor
        logger.debug("Step 1: Detecting license plate...")
        detection = self.detector.detect_best_plate(original_image)
        
        if detection is None:
            logger.warning("Tidak ada plat nomor terdeteksi")
            return self._create_no_detection_result(original_image, return_images)
        
        if detection.cropped_image is None or detection.cropped_image.size == 0:
            logger.warning("Crop gambar plat kosong")
            return self._create_error_result("Crop gambar plat kosong")

        # Step 2: Preprocessing gambar plat
        logger.debug("Step 2: Preprocessing plate image...")
        processed_plate = self.preprocessor.process(detection.cropped_image)

        # Step 3: OCR untuk membaca teks plat
        logger.debug("Step 3: Running OCR...")
        if self.debug:
            from pathlib import Path as _Path
            import cv2 as _cv2
            _Path("output/debug_crop").mkdir(parents=True, exist_ok=True)
            _cv2.imwrite(f"output/debug_crop/crop_{self._debug_counter:04d}.jpg", detection.cropped_image)
            self._debug_counter = getattr(self, '_debug_counter', 0) + 1

        if self.ocr.engine_type.value == "paddleocr":
            ocr_result = self.ocr.read(detection.cropped_image)
        else:
            ocr_result = self.ocr.read(processed_plate)

        # Step 4: Calculate overall confidence & determine status
        logger.debug("Step 4: Calculating confidence & status...")
        overall_confidence = self._calculate_overall_confidence(
            detection.confidence,
            ocr_result.confidence,
        )
        
        vehicle_status = self._determine_vehicle_status(
            detection_confidence=detection.confidence,
            ocr_confidence=ocr_result.confidence,
            overall_confidence=overall_confidence,
            has_plate_text=bool(ocr_result.text.strip()),
            is_valid_format=ocr_result.is_valid_format,
        )

        # Step 5: Annotate image (untuk visualisasi)
        annotated_image = None
        if return_images or self.debug:
            annotated_image = self._annotate_image(
                original_image,
                detection,
                ocr_result.text,
                vehicle_status,
            )

        # Create result
        result = ALPRResult(
            plate_text=ocr_result.text,
            raw_plate_text=ocr_result.raw_text,
            detection_confidence=detection.confidence,
            ocr_confidence=ocr_result.confidence,
            overall_confidence=overall_confidence,
            bbox=detection.bbox,
            vehicle_status=vehicle_status,
            is_valid_format=ocr_result.is_valid_format,
            ocr_engine_used=ocr_result.engine_used,
        )

        # Attach images jika diminta
        if return_images or self.debug:
            result.original_image = original_image
            result.cropped_plate = detection.cropped_image
            result.processed_plate = processed_plate
            result.annotated_image = annotated_image

        logger.info(
            f"ALPR selesai: plate='{ocr_result.text}' | "
            f"det_conf={detection.confidence:.3f} | "
            f"ocr_conf={ocr_result.confidence:.3f} | "
            f"overall={overall_confidence:.3f} | "
            f"status={vehicle_status.value}"
        )

        return result

    def process_video_frame(self, frame: np.ndarray) -> ALPRResult:
        """
        Process satu frame video (convenience method).
        Sama seperti process() tapi khusus untuk numpy array.

        Args:
            frame: Frame video (numpy array BGR)

        Returns:
            ALPRResult
        """
        return self.process(frame, return_images=False)

    def _calculate_overall_confidence(
        self,
        detection_confidence: float,
        ocr_confidence: float,
    ) -> float:
        """
        Hitung overall confidence dari detection dan OCR.
        Menggunakan weighted average (detection lebih penting).

        Weights:
            - Detection: 0.4 (lokalisasi plat)
            - OCR: 0.6 (membaca teks)
        """
        weighted = (detection_confidence * 0.4) + (ocr_confidence * 0.6)
        return weighted

    def _determine_vehicle_status(
        self,
        detection_confidence: float,
        ocr_confidence: float,
        overall_confidence: float,
        has_plate_text: bool,
        is_valid_format: bool,
    ) -> VehicleStatus:
        """
        Tentukan status kendaraan berdasarkan confidence dan validasi.

        Logic:
            - ACCEPTED: Overall confidence >= threshold DAN format valid
            - RETRY: Detection confidence OK tapi OCR confidence rendah
            - REJECTED: Detection gagal atau confidence terlalu rendah
        """
        # Case 1: Detection confidence terlalu rendah → RETRY
        if detection_confidence < self.detection_conf_threshold:
            return VehicleStatus.RETRY

        # Case 2: OCR confidence terlalu rendah → RETRY (scan ulang)
        if ocr_confidence < self.ocr_conf_threshold:
            return VehicleStatus.RETRY

        # Case 3: Overall confidence OK tapi tidak ada teks → REJECTED
        if not has_plate_text:
            return VehicleStatus.REJECTED

        # Case 4: Overall confidence OK dan format valid → ACCEPTED
        if overall_confidence >= self.overall_conf_threshold and is_valid_format:
            return VehicleStatus.ACCEPTED

        # Case 5: Overall confidence OK tapi format invalid → REJECTED
        if overall_confidence >= self.overall_conf_threshold and not is_valid_format:
            return VehicleStatus.REJECTED

        # Case 6: Overall confidence di bawah threshold → RETRY
        if overall_confidence < self.overall_conf_threshold:
            return VehicleStatus.RETRY

        # Default: REJECTED
        return VehicleStatus.REJECTED

    def _annotate_image(
        self,
        image: np.ndarray,
        detection: PlateDetection,
        plate_text: str,
        status: VehicleStatus,
    ) -> np.ndarray:
        """
        Annotate gambar dengan bounding box dan teks plat.

        Args:
            image: Gambar asli
            detection: Hasil deteksi plat
            plate_text: Teks plat nomor
            status: Status kendaraan

        Returns:
            Gambar yang sudah diannotate
        """
        annotated = image.copy()
        x1, y1, x2, y2 = detection.bbox

        # Warna berdasarkan status
        if status == VehicleStatus.ACCEPTED:
            color = (0, 255, 0)      # Hijau
            status_text = "ACCEPTED"
        elif status == VehicleStatus.RETRY:
            color = (0, 255, 255)    # Kuning
            status_text = "RETRY"
        else:  # REJECTED
            color = (0, 0, 255)      # Merah
            status_text = "REJECTED"

        # Gambar bounding box
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3)

        # Label: plate text + status
        label = f"{plate_text} [{status_text}]"
        font_scale = 0.7
        thickness = 2
        
        (label_w, label_h), _ = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness
        )

        # Background untuk label
        cv2.rectangle(
            annotated,
            (x1, y1 - label_h - 15),
            (x1 + label_w + 10, y1),
            color,
            -1,
        )

        # Teks label
        cv2.putText(
            annotated,
            label,
            (x1 + 5, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (255, 255, 255),
            thickness,
        )

        return annotated

    def _create_error_result(self, error_message: str) -> ALPRResult:
        """Create error result."""
        logger.error(f"ALPR Error: {error_message}")
        return ALPRResult(
            plate_text="",
            raw_plate_text="",
            detection_confidence=0.0,
            ocr_confidence=0.0,
            overall_confidence=0.0,
            bbox=None,
            vehicle_status=VehicleStatus.REJECTED,
            is_valid_format=False,
            ocr_engine_used="",
            error_message=error_message,
        )

    def _create_no_detection_result(
        self,
        image: np.ndarray,
        return_images: bool,
    ) -> ALPRResult:
        """Create result ketika tidak ada plat terdeteksi."""
        result = ALPRResult(
            plate_text="",
            raw_plate_text="",
            detection_confidence=0.0,
            ocr_confidence=0.0,
            overall_confidence=0.0,
            bbox=None,
            vehicle_status=VehicleStatus.REJECTED,
            is_valid_format=False,
            ocr_engine_used="",
            error_message="Tidak ada plat nomor terdeteksi",
        )

        if return_images or self.debug:
            result.original_image = image

        return result


# Convenience function untuk quick testing
def process_plate_image(
    image_path: str,
    output_path: Optional[str] = None,
) -> ALPRResult:
    """
    Quick function untuk process satu gambar plat.

    Args:
        image_path: Path ke gambar
        output_path: Path untuk save annotated image (optional)

    Returns:
        ALPRResult
    """
    pipeline = ALPRPipeline(debug=True)
    result = pipeline.process(image_path, return_images=True)

    # Save annotated image jika output_path diberikan
    if output_path and result.annotated_image is not None:
        cv2.imwrite(output_path, result.annotated_image)
        logger.info(f"Annotated image saved to: {output_path}")

    return result


if __name__ == "__main__":
    # Contoh penggunaan
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <image_path> [output_path]")
        sys.exit(1)

    image_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    result = process_plate_image(image_path, output_path)

    print("\n" + "=" * 60)
    print("ALPR PIPELINE RESULT")
    print("=" * 60)
    print(f"Plate Text:          {result.plate_text}")
    print(f"Raw Text:            {result.raw_plate_text}")
    print(f"Detection Conf:      {result.detection_confidence:.3f}")
    print(f"OCR Conf:            {result.ocr_confidence:.3f}")
    print(f"Overall Conf:        {result.overall_confidence:.3f}")
    print(f"Valid Format:        {result.is_valid_format}")
    print(f"Vehicle Status:      {result.vehicle_status.value}")
    print(f"OCR Engine:          {result.ocr_engine_used}")
    if result.error_message:
        print(f"Error:               {result.error_message}")
    print("=" * 60)