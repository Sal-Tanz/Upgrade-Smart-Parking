"""
Modul Klasifikasi Slot Parkir (Kosong/Terisi) menggunakan CNN.

Tujuan:
    - Mengklasifikasikan setiap slot parkir sebagai "kosong" atau "terisi"
    - Menggunakan CNN ringan (MobileNetV3 / EfficientNet-Lite)
    - Alternatif: Background Subtraction (MOG2) untuk setup tanpa training

Metode:
    1. Crop gambar slot dari kamera top-down
    2. Preprocessing (resize, normalize)
    3. Inference CNN atau Background Subtraction
    4. Output: 0 = Kosong, 1 = Terisi

Penggunaan:
    classifier = SlotClassifier(model_path="ml/models/slot_classifier.onnx")
    status = classifier.classify(slot_image)
    print(status)  # "kosong" atau "terisi"
"""

from pathlib import Path
from typing import Optional, Literal
from dataclasses import dataclass

import cv2
import numpy as np
from loguru import logger

try:
    import torch
    import torch.nn as nn
    import torchvision.transforms as transforms
    import torchvision.models as models
except ImportError:
    torch = None
    logger.warning("PyTorch tidak terinstall. Jalankan: pip install torch torchvision")

try:
    import onnxruntime as ort
except ImportError:
    ort = None
    logger.warning("ONNX Runtime tidak terinstall (optional untuk inference cepat)")


@dataclass
class SlotClassification:
    """Hasil klasifikasi satu slot."""
    slot_id: str
    status: Literal["kosong", "terisi", "unknown"]
    confidence: float
    method: str  # "cnn" atau "background_subtraction"


class SlotClassifier:
    """
    Klasifikasi slot parkir menggunakan CNN atau Background Subtraction.

    Args:
        model_path: Path ke model CNN (.pt atau .onnx)
        method: Metode klasifikasi ("cnn" atau "background_subtraction")
        confidence_threshold: Threshold confidence (default 0.5)
        device: Device inference ("cpu" atau "cuda")
        input_size: Ukuran input untuk CNN (default 224x224)
    """

    STATUS_KOSONG = "kosong"
    STATUS_TERISI = "terisi"
    STATUS_UNKNOWN = "unknown"

    # Class mapping: 0 = kosong, 1 = terisi
    CLASS_NAMES = ["kosong", "terisi"]

    def __init__(
        self,
        model_path: str = "ml/models/slot_classifier.onnx",
        method: Literal["cnn", "background_subtraction"] = "cnn",
        confidence_threshold: float = 0.5,
        device: str = "cpu",
        input_size: int = 224,
    ):
        self.method = method
        self.confidence_threshold = confidence_threshold
        self.device = device
        self.input_size = input_size

        # Initialize berdasarkan method
        if method == "cnn":
            self._init_cnn(model_path)
        elif method == "background_subtraction":
            self._init_background_subtraction()
        else:
            raise ValueError(f"Method tidak dikenal: {method}")

        logger.info(
            f"SlotClassifier siap | method={method} | "
            f"conf_thresh={confidence_threshold} | device={device}"
        )

    def _init_cnn(self, model_path: str):
        """Initialize CNN model."""
        model_file = Path(model_path)

        if not model_file.exists():
            logger.warning(
                f"Model tidak ditemukan: {model_path}. "
                "Menggunakan MobileNetV3 pretrained sebagai fallback. "
                "Untuk hasil optimal, lakukan fine-tuning pada dataset slot parkir."
            )
            # Fallback ke MobileNetV3 pretrained
            self._init_mobilenet()
            return

        # Load model berdasarkan format
        if model_path.endswith(".onnx"):
            self._load_onnx_model(model_path)
        elif model_path.endswith(".pt"):
            self._load_pytorch_model(model_path)
        else:
            raise ValueError(f"Format model tidak didukung: {model_path}")

    def _init_mobilenet(self):
        """Initialize MobileNetV3 sebagai fallback."""
        if torch is None:
            raise ImportError("PyTorch wajib untuk method CNN")

        self.model = models.mobilenet_v3_small(pretrained=True)
        # Modify classifier head untuk 2 classes (kosong/terisi)
        self.model.classifier[-1] = nn.Linear(1024, 2)
        self.model.eval()
        self.model.to(self.device)

        # Transform untuk preprocessing
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((self.input_size, self.input_size)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            ),
        ])

        self.model_type = "pytorch"

    def _load_pytorch_model(self, model_path: str):
        """Load PyTorch model (.pt)."""
        if torch is None:
            raise ImportError("PyTorch wajib untuk load .pt model")

        # SECURITY: weights_only=True prevents arbitrary code execution during unpickling
        # See: https://pytorch.org/docs/stable/notes/serialization.html
        self.model = torch.load(model_path, map_location=self.device, weights_only=True)
        self.model.eval()
        self.model.to(self.device)

        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((self.input_size, self.input_size)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            ),
        ])

        self.model_type = "pytorch"

    def _load_onnx_model(self, model_path: str):
        """Load ONNX model (.onnx) untuk inference cepat."""
        if ort is None:
            logger.warning("ONNX Runtime tidak tersedia, fallback ke PyTorch")
            self._init_mobilenet()
            return

        self.ort_session = ort.InferenceSession(model_path)
        self.model_type = "onnx"

    def _init_background_subtraction(self):
        """Initialize Background Subtraction (MOG2) sebagai alternatif tanpa training."""
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500,
            varThreshold=50,
            detectShadows=False,
        )
        self.pixel_ratio_threshold = 0.1  # 10% pixel = terisi

    def classify(self, image: np.ndarray, slot_id: str = "") -> SlotClassification:
        """
        Klasifikasi slot parkir.

        Args:
            image: Gambar slot (crop dari kamera top-down)
            slot_id: ID slot (untuk logging)

        Returns:
            SlotClassification berisi status dan confidence
        """
        if image is None or image.size == 0:
            logger.warning(f"Gambar slot {slot_id} kosong")
            return SlotClassification(
                slot_id=slot_id,
                status=self.STATUS_UNKNOWN,
                confidence=0.0,
                method=self.method,
            )

        if self.method == "cnn":
            return self._classify_cnn(image, slot_id)
        else:
            return self._classify_background_subtraction(image, slot_id)

    def _classify_cnn(self, image: np.ndarray, slot_id: str) -> SlotClassification:
        """Klasifikasi menggunakan CNN."""
        # Preprocessing
        if self.model_type == "pytorch":
            return self._classify_pytorch(image, slot_id)
        else:
            return self._classify_onnx(image, slot_id)

    def _classify_pytorch(self, image: np.ndarray, slot_id: str) -> SlotClassification:
        """Inference menggunakan PyTorch."""
        # Convert BGR ke RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Transform
        input_tensor = self.transform(image_rgb).unsqueeze(0).to(self.device)

        # Inference
        with torch.no_grad():
            output = self.model(input_tensor)
            probabilities = torch.nn.functional.softmax(output[0], dim=0)
            confidence, predicted_class = torch.max(probabilities, 0)

        # Convert ke Python types
        predicted_class = int(predicted_class.cpu())
        confidence = float(confidence.cpu())

        # Determine status
        if confidence < self.confidence_threshold:
            status = self.STATUS_UNKNOWN
        else:
            status = self.CLASS_NAMES[predicted_class]

        logger.debug(
            f"Slot {slot_id} classified: {status} "
            f"(conf={confidence:.3f}, class={predicted_class})"
        )

        return SlotClassification(
            slot_id=slot_id,
            status=status,
            confidence=confidence,
            method="cnn",
        )

    def _classify_onnx(self, image: np.ndarray, slot_id: str) -> SlotClassification:
        """Inference menggunakan ONNX Runtime."""
        # Convert BGR ke RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Resize dan normalize
        image_resized = cv2.resize(image_rgb, (self.input_size, self.input_size))
        image_normalized = image_resized.astype(np.float32) / 255.0
        image_normalized = (image_normalized - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]

        # Transpose ke NCHW format
        input_tensor = np.transpose(image_normalized, (2, 0, 1))
        input_tensor = np.expand_dims(input_tensor, axis=0)

        # VALIDATION: Verify input shape matches ONNX model expectations
        # See: https://onnxruntime.ai/docs/get-started/with-python.html
        input_name = self.ort_session.get_inputs()[0].name
        expected_shape = [1, 3, self.input_size, self.input_size]  # NCHW format
        actual_shape = list(input_tensor.shape)

        if actual_shape != expected_shape:
            logger.error(
                f"ONNX input shape mismatch! Expected {expected_shape}, got {actual_shape}. "
                f"Check model input configuration for slot {slot_id}."
            )
            return SlotClassification(
                slot_id=slot_id,
                status="unknown",  # Use valid Literal value instead of "error"
                confidence=0.0,
                method="onnx"
            )

        # Inference
        ort_inputs = {self.ort_session.get_inputs()[0].name: input_tensor}
        ort_outputs = self.ort_session.run(None, ort_inputs)

        # Parse output
        output = ort_outputs[0][0]
        # Stable softmax: subtract max to prevent overflow
        output_shifted = output - np.max(output)
        exp_output = np.exp(output_shifted)
        probabilities = exp_output / np.sum(exp_output)
        predicted_class = int(np.argmax(probabilities))
        confidence = float(probabilities[predicted_class])

        # Determine status
        if confidence < self.confidence_threshold:
            status = self.STATUS_UNKNOWN
        else:
            status = self.CLASS_NAMES[predicted_class]

        logger.debug(
            f"Slot {slot_id} classified (ONNX): {status} "
            f"(conf={confidence:.3f}, class={predicted_class})"
        )

        return SlotClassification(
            slot_id=slot_id,
            status=status,
            confidence=confidence,
            method="cnn",
        )

    def _classify_background_subtraction(
        self,
        image: np.ndarray,
        slot_id: str,
    ) -> SlotClassification:
        """
        Klasifikasi menggunakan Background Subtraction (MOG2).
        Alternatif tanpa training CNN.

        Logic:
            - Hitung foreground mask (perbedaan dari background)
            - Jika pixel ratio > threshold → terisi
            - Jika pixel ratio < threshold → kosong
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Apply background subtraction
        fg_mask = self.bg_subtractor.apply(gray)

        # Calculate pixel ratio (foreground pixels / total pixels)
        total_pixels = fg_mask.size
        foreground_pixels = np.sum(fg_mask > 0)
        pixel_ratio = foreground_pixels / total_pixels

        # Determine status
        if pixel_ratio > self.pixel_ratio_threshold:
            status = self.STATUS_TERISI
            confidence = min(pixel_ratio * 2, 1.0)  # Scale confidence
        else:
            status = self.STATUS_KOSONG
            confidence = 1.0 - pixel_ratio

        logger.debug(
            f"Slot {slot_id} classified (BG Sub): {status} "
            f"(pixel_ratio={pixel_ratio:.3f}, conf={confidence:.3f})"
        )

        return SlotClassification(
            slot_id=slot_id,
            status=status,
            confidence=confidence,
            method="background_subtraction",
        )

    def classify_batch(
        self,
        images: dict[str, np.ndarray],
    ) -> dict[str, SlotClassification]:
        """
        Klasifikasi multiple slots sekaligus.

        Args:
            images: Dict mapping slot_id -> image

        Returns:
            Dict mapping slot_id -> SlotClassification
        """
        results = {}
        for slot_id, image in images.items():
            results[slot_id] = self.classify(image, slot_id)

        return results