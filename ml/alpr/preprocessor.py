"""
Modul Preprocessing Plat Nomor untuk ALPR.

Tahap preprocessing sebelum OCR:
    1. Grayscale conversion
    2. Adaptive thresholding (binarisasi)
    3. Deskew / perspective correction
    4. Denoising
    5. Resize & normalization

Tujuan: Meningkatkan akurasi OCR dengan menghasilkan gambar plat yang bersih
dan terstandardisasi.

Penggunaan:
    preprocessor = PlatePreprocessor()
    processed = preprocessor.process(cropped_plate_image)
"""

import cv2
import numpy as np
from loguru import logger


class PlatePreprocessor:
    """
    Preprocessing gambar plat nomor sebelum OCR.

    Args:
        target_width: Lebar target setelah resize (default 300)
        target_height: Tinggi target setelah resize (default 100)
        enable_deskew: Aktifkan deskew/perspective correction (default True)
        enable_denoise: Aktifkan denoising (default True)
        debug: Tampilkan intermediate steps (default False)
    """

    def __init__(
        self,
        target_width: int = 300,
        target_height: int = 100,
        enable_deskew: bool = True,
        enable_denoise: bool = True,
        debug: bool = False,
    ):
        self.target_width = target_width
        self.target_height = target_height
        self.enable_deskew = enable_deskew
        self.enable_denoise = enable_denoise
        self.debug = debug

        logger.info(
            f"PlatePreprocessor siap | "
            f"target_size=({target_width}x{target_height}) | "
            f"deskew={enable_deskew} | denoise={enable_denoise}"
        )

    def process(self, image: np.ndarray) -> np.ndarray:
        """
        Pipeline preprocessing lengkap.

        Args:
            image: Gambar plat nomor hasil crop (BGR numpy array)

        Returns:
            Gambar yang sudah dipreprocess, siap untuk OCR
        """
        if image is None or image.size == 0:
            logger.warning("Gambar input kosong")
            return image

        processed = image.copy()

        # Step 1: Grayscale conversion
        processed = self._to_grayscale(processed)
        if self.debug:
            logger.debug("Step 1: Grayscale conversion selesai")

        # Step 2: Denoising (sebelum thresholding)
        if self.enable_denoise:
            processed = self._denoise(processed)
            if self.debug:
                logger.debug("Step 2: Denoising selesai")

        # Step 3: Deskew / perspective correction
        if self.enable_deskew:
            processed = self._deskew(processed)
            if self.debug:
                logger.debug("Step 3: Deskew selesai")

        # Step 4: Adaptive thresholding
        processed = self._adaptive_threshold(processed)
        if self.debug:
            logger.debug("Step 4: Adaptive thresholding selesai")

        # Step 5: Resize & normalize
        processed = self._resize_and_normalize(processed)
        if self.debug:
            logger.debug("Step 5: Resize & normalize selesai")

        return processed

    def _to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """Konversi BGR ke grayscale."""
        if len(image.shape) == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image

    def _denoise(self, image: np.ndarray) -> np.ndarray:
        """
        Denoising menggunakan Non-Local Means Denoising.
        Efektif untuk noise Gaussian dan salt-and-pepper.
        """
        # Non-Local Means Denoising (lebih baik dari Gaussian blur untuk teks)
        denoised = cv2.fastNlMeansDenoising(
            image,
            h=10,           # Filter strength (10 untuk moderate noise)
            templateWindowSize=7,
            searchWindowSize=21,
        )
        return denoised

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        """
        Deskew / perspective correction.
        Mengoreksi kemiringan plat nomor untuk hasil OCR yang lebih baik.
        """
        # Deteksi edges menggunakan Canny
        edges = cv2.Canny(image, 50, 150, apertureSize=3)

        # Deteksi garis menggunakan Hough Line Transform
        lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)

        if lines is None or len(lines) == 0:
            logger.debug("Tidak ada garis terdeteksi untuk deskew")
            return image

        # Hitung angle kemiringan dari garis-garis yang terdeteksi
        angles = []
        for line in lines:
            rho, theta = line[0]
            angle = np.degrees(theta) - 90
            angles.append(angle)

        # Ambil median angle (lebih robust terhadap outlier)
        median_angle = np.median(angles)

        # Hanya lakukan rotasi jika angle signifikan (> 2 derajat)
        if abs(median_angle) < 2:
            logger.debug(f"Angle terlalu kecil ({median_angle:.2f}°), skip deskew")
            return image

        logger.debug(f"Deskew angle: {median_angle:.2f}°")

        # Rotasi gambar
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(
            image,
            rotation_matrix,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )

        return rotated

    def _adaptive_threshold(self, image: np.ndarray) -> np.ndarray:
        """
        Adaptive thresholding untuk binarisasi.
        Lebih baik dari global threshold untuk kondisi pencahayaan tidak merata.
        """
        # Adaptive Gaussian thresholding
        binary = cv2.adaptiveThreshold(
            image,
            maxValue=255,
            adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            thresholdType=cv2.THRESH_BINARY,
            blockSize=11,    # Ukuran neighborhood (harus ganjil)
            C=2,             # Constant yang dikurangkan dari mean
        )
        return binary

    def _resize_and_normalize(self, image: np.ndarray) -> np.ndarray:
        """
        Resize ke ukuran target dan normalisasi.
        OCR engine biasanya bekerja lebih baik dengan ukuran konsisten.
        """
        # Resize dengan aspect ratio preservation
        h, w = image.shape[:2]
        aspect_ratio = w / h

        # Hitung ukuran baru dengan menjaga aspect ratio
        if aspect_ratio > (self.target_width / self.target_height):
            # Width-limited
            new_w = self.target_width
            new_h = int(new_w / aspect_ratio)
        else:
            # Height-limited
            new_h = self.target_height
            new_w = int(new_h * aspect_ratio)

        # Resize menggunakan INTER_AREA untuk downscaling (lebih tajam)
        if new_w < w or new_h < h:
            resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

        # Pad dengan border putih untuk mencapai target size exact
        pad_top = (self.target_height - new_h) // 2
        pad_bottom = self.target_height - new_h - pad_top
        pad_left = (self.target_width - new_w) // 2
        pad_right = self.target_width - new_w - pad_left

        padded = cv2.copyMakeBorder(
            resized,
            pad_top,
            pad_bottom,
            pad_left,
            pad_right,
            borderType=cv2.BORDER_CONSTANT,
            value=255,  # Putih (background)
        )

        return padded

    def enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """
        Enhance kontras menggunakan CLAHE (Contrast Limited Adaptive Histogram Equalization).
        Berguna untuk plat dengan kontras rendah.
        """
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(image)
        return enhanced

    def remove_shadow(self, image: np.ndarray) -> np.ndarray:
        """
        Hapus bayangan menggunakan morphological operations.
        Berguna untuk plat dengan bayangan yang mengganggu OCR.
        """
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Morphological closing (dilation followed by erosion)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        closed = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)

        # Subtract original dari closed untuk mendapat shadow
        shadow = cv2.subtract(closed, image)

        # Normalize shadow
        shadow_normalized = cv2.normalize(shadow, None, 0, 255, cv2.NORM_MINMAX)

        # Add shadow back ke original
        result = cv2.add(image, shadow_normalized)

        return result