"""
Modul Segmentasi Garis Parkir menggunakan Hough Line Transform.

Tujuan:
    - Mendeteksi garis-garis parkir dari gambar top-down/CCTV
    - Menghasilkan koordinat polygon untuk setiap slot parkir
    - Output: JSON konfigurasi slot dengan koordinat dan label cluster

Metode:
    1. Preprocessing (grayscale, blur, edge detection)
    2. Hough Line Transform untuk deteksi garis
    3. Grouping lines menjadi rectangles (slots)
    4. Generate slot configuration (JSON)

Penggunaan:
    detector = SlotDetector()
    slots = detector.detect_slots(image)
    detector.save_config(slots, "data/slot_config.json")
"""

import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

import cv2
import numpy as np
from loguru import logger


@dataclass
class ParkingSlot:
    """Definisi satu slot parkir."""
    slot_id: str                                      # ID slot (M-01, O-01, dll)
    cluster: str                                      # Cluster: "Merah" atau "Orange"
    polygon: list[list[int]]                          # 4 titik polygon [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    center: tuple[int, int]                           # Titik tengah slot
    width: int                                        # Lebar slot (pixel)
    height: int                                       # Tinggi slot (pixel)
    status: str = "unknown"                           # "kosong", "terisi", "unknown"


class SlotDetector:
    """
    Deteksi slot parkir menggunakan Hough Line Transform.

    Args:
        canny_low_threshold: Low threshold untuk Canny edge detection (default 50)
        canny_high_threshold: High threshold untuk Canny (default 150)
        hough_threshold: Threshold untuk Hough Line Transform (default 100)
        min_line_length: Panjang minimum garis (default 100)
        max_line_gap: Gap maksimum antar garis (default 10)
        slot_min_area: Area minimum slot (pixel^2) (default 5000)
        slot_max_area: Area maksimum slot (pixel^2) (default 50000)
    """

    def __init__(
        self,
        canny_low_threshold: int = 50,
        canny_high_threshold: int = 150,
        hough_threshold: int = 100,
        min_line_length: int = 100,
        max_line_gap: int = 10,
        slot_min_area: int = 5000,
        slot_max_area: int = 50000,
    ):
        self.canny_low = canny_low_threshold
        self.canny_high = canny_high_threshold
        self.hough_threshold = hough_threshold
        self.min_line_length = min_line_length
        self.max_line_gap = max_line_gap
        self.slot_min_area = slot_min_area
        self.slot_max_area = slot_max_area

        logger.info(
            f"SlotDetector siap | "
            f"canny=({canny_low_threshold}, {canny_high_threshold}) | "
            f"hough_thresh={hough_threshold} | "
            f"slot_area=({slot_min_area}, {slot_max_area})"
        )

    def detect_slots(
        self,
        image: np.ndarray,
        cluster_assignments: Optional[dict[str, str]] = None,
    ) -> list[ParkingSlot]:
        """
        Deteksi slot parkir dari gambar.

        Args:
            image: Gambar area parkir (BGR numpy array)
            cluster_assignments: Dict mapping slot_id -> cluster
                Contoh: {"slot_1": "Merah", "slot_2": "Orange"}
                Jika None, semua slot default ke "Orange"

        Returns:
            List ParkingSlot yang terdeteksi
        """
        if image is None or image.size == 0:
            logger.warning("Gambar input kosong")
            return []

        # Step 1: Preprocessing
        logger.debug("Step 1: Preprocessing image...")
        processed = self._preprocess(image)

        # Step 2: Edge detection
        logger.debug("Step 2: Detecting edges...")
        edges = self._detect_edges(processed)

        # Step 3: Hough Line Transform
        logger.debug("Step 3: Detecting lines with Hough Transform...")
        lines = self._detect_lines(edges)

        if lines is None or len(lines) == 0:
            logger.warning("Tidak ada garis terdeteksi")
            return []

        # Step 4: Group lines into rectangles (slots)
        logger.debug("Step 4: Grouping lines into slots...")
        rectangles = self._group_lines_into_rectangles(lines, edges.shape)

        # Step 5: Filter rectangles by area
        logger.debug("Step 5: Filtering slots by area...")
        filtered_rects = self._filter_rectangles(rectangles)

        # Step 6: Create ParkingSlot objects
        logger.debug("Step 6: Creating ParkingSlot objects...")
        slots = self._create_slots(filtered_rects, cluster_assignments)

        logger.info(f"Deteksi selesai: {len(slots)} slot ditemukan")

        return slots

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """Preprocessing: grayscale + Gaussian blur."""
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Gaussian blur untuk reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        return blurred

    def _detect_edges(self, image: np.ndarray) -> np.ndarray:
        """Deteksi edges menggunakan Canny."""
        edges = cv2.Canny(image, self.canny_low, self.canny_high)
        return edges

    def _detect_lines(self, edges: np.ndarray) -> Optional[np.ndarray]:
        """
        Deteksi garis menggunakan Probabilistic Hough Line Transform.

        See: https://docs.opencv.org/4.x/dd/d1a/group__imgproc__feature.html#ga8618180a5948286384e3b7ca02f6feeb

        Parameters:
        - rho: Distance resolution in pixels (1 = 1 pixel precision)
        - theta: Angle resolution in radians (π/180 = 1 degree precision)
        - threshold: Accumulator threshold. Higher = fewer lines detected (only strong lines).
                    Lower = more lines but may include noise. Typical range: 50-200.
        - minLineLength: Minimum line length to accept (in pixels)
        - maxLineGap: Maximum gap between line segments to treat as single line
        """
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=self.hough_threshold,
            minLineLength=self.min_line_length,
            maxLineGap=self.max_line_gap,
        )
        return lines

    def _group_lines_into_rectangles(
        self,
        lines: np.ndarray,
        image_shape: tuple,
    ) -> list[list[list[int]]]:
        """
        Group garis-garis menjadi rectangles (4 titik polygon).
        
        Strategi:
            1. Cluster lines berdasarkan angle (horizontal vs vertical)
            2. Find intersections
            3. Group intersections menjadi rectangles
        
        Returns:
            List of rectangles, setiap rectangle = [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        """
        if lines is None or len(lines) == 0:
            return []

        # Simplified approach: use contour detection instead of line grouping
        # This is more robust for real-world parking lot images
        
        # Create a mask from lines
        mask = np.zeros(image_shape, dtype=np.uint8)
        for line in lines:
            x1, y1, x2, y2 = line[0]
            cv2.line(mask, (x1, y1), (x2, y2), 255, 2)

        # Dilate to connect nearby lines
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        mask = cv2.dilate(mask, kernel, iterations=2)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        rectangles = []
        for contour in contours:
            # Approximate contour to polygon
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)

            # Check if it's a quadrilateral (4 vertices)
            if len(approx) == 4:
                rect = [point[0].tolist() for point in approx]
                rectangles.append(rect)

        return rectangles

    def _filter_rectangles(
        self,
        rectangles: list[list[list[int]]],
    ) -> list[list[list[int]]]:
        """Filter rectangles berdasarkan area."""
        filtered = []

        for rect in rectangles:
            # Calculate area using contour
            contour = np.array(rect, dtype=np.int32).reshape((-1, 1, 2))
            area = cv2.contourArea(contour)

            if self.slot_min_area <= area <= self.slot_max_area:
                filtered.append(rect)

        logger.debug(f"Filtered: {len(filtered)}/{len(rectangles)} rectangles")

        return filtered

    def _create_slots(
        self,
        rectangles: list[list[list[int]]],
        cluster_assignments: Optional[dict[str, str]] = None,
    ) -> list[ParkingSlot]:
        """Create ParkingSlot objects dari rectangles."""
        slots = []

        for i, rect in enumerate(rectangles):
            slot_id = f"slot_{i+1:03d}"
            cluster = "Orange"  # Default

            if cluster_assignments and slot_id in cluster_assignments:
                cluster = cluster_assignments[slot_id]

            # Calculate center
            xs = [point[0] for point in rect]
            ys = [point[1] for point in rect]

            # Guard against empty polygons (approxPolyDP can return empty arrays)
            if not xs or not ys:
                logger.warning(f"Empty polygon for {slot_id}, skipping")
                continue

            center_x = int(sum(xs) / len(xs))
            center_y = int(sum(ys) / len(ys))

            # Calculate width and height (approximate)
            width = max(xs) - min(xs)
            height = max(ys) - min(ys)

            slot = ParkingSlot(
                slot_id=slot_id,
                cluster=cluster,
                polygon=rect,
                center=(center_x, center_y),
                width=width,
                height=height,
                status="unknown",
            )

            slots.append(slot)

        return slots

    def save_config(self, slots: list[ParkingSlot], output_path: str):
        """
        Save slot configuration ke JSON file.

        Args:
            slots: List ParkingSlot
            output_path: Path untuk save JSON
        """
        config = {
            "slots": [asdict(slot) for slot in slots],
            "total_slots": len(slots),
            "merah_count": sum(1 for s in slots if s.cluster == "Merah"),
            "orange_count": sum(1 for s in slots if s.cluster == "Orange"),
        }

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(config, f, indent=2)

        logger.info(
            f"Slot config saved to {output_path} | "
            f"total={len(slots)} | "
            f"merah={config['merah_count']} | "
            f"orange={config['orange_count']}"
        )

    def load_config(self, config_path: str) -> list[ParkingSlot]:
        """
        Load slot configuration dari JSON file.

        Args:
            config_path: Path ke JSON config

        Returns:
            List ParkingSlot
        """
        with open(config_path, "r") as f:
            config = json.load(f)

        slots = []
        for slot_data in config["slots"]:
            # Convert list back to tuple for center
            slot_data["center"] = tuple(slot_data["center"])
            slot = ParkingSlot(**slot_data)
            slots.append(slot)

        logger.info(f"Loaded {len(slots)} slots from {config_path}")

        return slots

    def draw_slots(
        self,
        image: np.ndarray,
        slots: list[ParkingSlot],
        show_labels: bool = True,
    ) -> np.ndarray:
        """
        Gambar slot parkir pada gambar.

        Args:
            image: Gambar asli
            slots: List ParkingSlot
            show_labels: Tampilkan label slot ID

        Returns:
            Gambar dengan slot tergambar
        """
        annotated = image.copy()

        for slot in slots:
            # Warna berdasarkan cluster dan status
            if slot.cluster == "Merah":
                if slot.status == "kosong":
                    color = (0, 200, 255)  # Orange terang
                elif slot.status == "terisi":
                    color = (0, 0, 255)    # Merah
                else:
                    color = (0, 165, 255)  # Orange
            else:  # Orange cluster
                if slot.status == "kosong":
                    color = (0, 255, 0)    # Hijau
                elif slot.status == "terisi":
                    color = (255, 165, 0)  # Orange (BGR)
                else:
                    color = (255, 255, 0)  # Cyan

            # Draw polygon
            polygon = np.array(slot.polygon, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(annotated, [polygon], True, color, 2)

            # Draw label
            if show_labels:
                label = f"{slot.slot_id}"
                cv2.putText(
                    annotated,
                    label,
                    slot.center,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    2,
                )

        return annotated