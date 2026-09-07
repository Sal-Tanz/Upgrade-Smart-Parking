"""
Modul Deteksi Plat Nomor menggunakan YOLOv8.

Tahap 1 dari pipeline ALPR:
    - Input: Frame video/gambar dari kamera (min. 1080p)
    - Output: Bounding box koordinat area plat nomor + confidence score
    - Model: YOLOv8 fine-tuned untuk plat nomor Indonesia
    - Target mAP: >= 0.90 pada IoU 0.5

Penggunaan:
    detector = PlateDetector(model_path="ml/models/yolov8_plate.pt")
    detections = detector.detect(image)
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import cv2
import numpy as np
from loguru import logger

try:
    import torch
except ImportError:
    torch = None

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None
    logger.warning("ultralytics tidak terinstall. " "Jalankan: pip install ultralytics")


@dataclass
class PlateDetection:
    """Hasil deteksi satu plat nomor."""

    bbox: tuple[float, float, float, float]  # x1, y1, x2, y2 (pixel)
    confidence: float  # confidence score 0-1
    class_id: int  # class ID (0 = plate)
    cropped_image: Optional[np.ndarray] = None  # crop gambar plat


class PlateDetector:
    """
    Deteksi plat nomor menggunakan YOLOv8.

    Args:
        model_path: Path ke file model YOLOv8 (.pt)
        confidence_threshold: Threshold minimum confidence (default 0.5)
        iou_threshold: Threshold NMS IoU (default 0.45)
        device: Device inference ("cpu", "cuda", "mps")
        imgsz: Ukuran input image (default 640)
    """

    DEFAULT_MODEL_PATH = "ml/models/best.pt"
    PRETRAINED_MODEL = "yolov8n.pt"  # fallback jika model custom belum ada

    def __init__(
        self,
        model_path: str = DEFAULT_MODEL_PATH,
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        device: str = "cuda",
        imgsz: int = 416,
    ):
        if YOLO is None:
            raise ImportError(
                "ultralytics wajib terinstall. " "Jalankan: pip install ultralytics"
            )

        if device == "cuda" and (torch is None or not torch.cuda.is_available()):
            logger.info("CUDA tidak tersedia atau GPU tidak terdeteksi, beralih ke device='cpu'")
            device = "cpu"

        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        self.imgsz = imgsz

        # Load model: gunakan custom model jika ada, fallback ke pretrained
        model_file = Path(model_path)
        if model_file.exists():
            logger.info(f"Memuat model custom: {model_path}")
            self.model = YOLO(str(model_file))
            self.is_custom = True
        else:
            logger.warning(
                f"⚠️  Model custom tidak ditemukan: {model_path}\n"
                f"   Menggunakan pretrained {self.PRETRAINED_MODEL} sebagai fallback.\n"
                "   ⚠️  PERINGATAN: Model ini TIDAK di-train untuk plat nomor Indonesia.\n"
                "   Hasil deteksi mungkin tidak akurat. Untuk hasil optimal:\n"
                f"   1. Siapkan dataset plat nomor Indonesia (lihat {Path('ml/training')})\n"
                "   2. Fine-tune model YOLOv8 dengan dataset tersebut\n"
                f"   3. Export ke {model_path}"
            )
            self.model = YOLO(self.PRETRAINED_MODEL)
            self.is_custom = False

        logger.info(
            f"PlateDetector siap | device={device} | "
            f"conf_thresh={confidence_threshold} | imgsz={imgsz}"
        )

    def detect(self, image: np.ndarray) -> list[PlateDetection]:
        """
        Deteksi plat nomor pada gambar.

        Args:
            image: Gambar input (numpy array BGR dari OpenCV)

        Returns:
            List PlateDetection berisi semua plat yang terdeteksi,
            diurutkan berdasarkan confidence (tertinggi dulu).
        """
        if image is None or image.size == 0:
            logger.warning("Gambar input kosong atau invalid")
            return []

        # Inference menggunakan YOLOv8
        results = self.model(
            image,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            device=self.device,
            imgsz=self.imgsz,
            verbose=False,
        )

        detections = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for box in boxes:
                # Extract bounding box (x1, y1, x2, y2)
                xyxy = box.xyxy[0].cpu().numpy()
                x1, y1, x2, y2 = map(int, xyxy)

                # Confidence score
                conf = float(box.conf[0].cpu().numpy())

                # Class ID
                cls_id = int(box.cls[0].cpu().numpy())

                # If using generic COCO fallback (80 classes), ignore non-vehicle classes
                # (e.g. class 0 is 'person' in COCO). Only inspect vehicle regions (car=2, motorcycle=3, bus=5, truck=7).
                if not self.is_custom and len(self.model.names) >= 80:
                    if cls_id not in (2, 3, 5, 7):
                        continue

                # Crop gambar plat dari image asli dengan padding
                h, w = image.shape[:2]
                bw = x2 - x1
                bh = y2 - y1
                pad_x = int(bw * 0.15)
                pad_y = int(bh * 0.3)
                x1_crop = max(0, x1 - pad_x)
                y1_crop = max(0, y1 - pad_y)
                x2_crop = min(w, x2 + pad_x)
                y2_crop = min(h, y2 + pad_y)
                cropped = image[y1_crop:y2_crop, x1_crop:x2_crop].copy()

                detections.append(
                    PlateDetection(
                        bbox=(x1, y1, x2, y2),
                        confidence=conf,
                        class_id=cls_id,
                        cropped_image=cropped if cropped.size > 0 else None,
                    )
                )

        # Urutkan berdasarkan confidence (tertinggi dulu)
        detections.sort(key=lambda d: d.confidence, reverse=True)

        logger.debug(
            f"Deteksi selesai: {len(detections)} plat ditemukan "
            f"(conf >= {self.confidence_threshold})"
        )

        return detections

    def detect_best_plate(self, image: np.ndarray) -> Optional[PlateDetection]:
        """
        Deteksi dan kembalikan hanya plat dengan confidence tertinggi.

        Args:
            image: Gambar input (numpy array BGR)

        Returns:
            PlateDetection dengan confidence tertinggi, atau None jika tidak ada
        """
        detections = self.detect(image)
        return detections[0] if detections else None

    def draw_detections(
        self, image: np.ndarray, detections: list[PlateDetection]
    ) -> np.ndarray:
        """
        Gambar bounding box deteksi pada gambar.

        Args:
            image: Gambar asli
            detections: List hasil deteksi

        Returns:
            Gambar dengan bounding box tergambar
        """
        annotated = image.copy()

        for det in detections:
            x1, y1, x2, y2 = det.bbox
            conf = det.confidence

            # Warna box: hijau (conf tinggi), kuning (sedang), merah (rendah)
            if conf >= 0.8:
                color = (0, 255, 0)  # Hijau
            elif conf >= 0.6:
                color = (0, 255, 255)  # Kuning
            else:
                color = (0, 0, 255)  # Merah

            # Gambar rectangle
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            # Label: confidence score
            label = f"Plate {conf:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            cv2.rectangle(
                annotated,
                (x1, y1 - label_size[1] - 10),
                (x1 + label_size[0], y1),
                color,
                -1,
            )
            cv2.putText(
                annotated,
                label,
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2,
            )

        return annotated
