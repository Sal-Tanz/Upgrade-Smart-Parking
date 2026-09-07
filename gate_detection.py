"""Dual-lane license plate detection and gate control.

The gate controller deliberately prefers false negatives over false positives:
- OCR text is only reused while the same bounding box is still tracked.
- A lane unlocks after the vehicle disappears for several frames.
- Registered plates are matched exactly after normalization; substring matches
  are not accepted for access control.
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path


import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from ml.alpr.pipeline import ALPRPipeline
from ml.alpr.ocr import PlateOCR


def parse_args():
    parser = argparse.ArgumentParser(description="Gate Control Dual Lane")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--video", type=str, default=None, help="File video lokal atau URL stream")
    source.add_argument("--camera", type=int, default=None, help="Indeks kamera USB/webcam")
    source.add_argument("--stream", type=str, default=None, help="URL stream RTSP atau m3u8")
    source.add_argument("--camera-id", type=int, default=None, help="ID kamera dari database parking.db")
    parser.add_argument("--model", type=str, default="ml/models/best.pt")
    parser.add_argument("--conf", type=float, default=0.2)
    # CPU is the safe default. Users with CUDA can explicitly pass --device cuda.
    parser.add_argument("--device", type=str, default="cpu")
    parser.add_argument("--imgsz", type=int, default=416)
    parser.add_argument("--db", type=str, default="data/plate_database.json")
    parser.add_argument("--save", type=str, default=None)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--ocr-interval", type=int, default=10)
    parser.add_argument(
        "--gate-duration", type=float, default=120.0,
        help="Durasi palang terbuka dalam detik (default: 120)",
    )
    parser.add_argument("--loop", action="store_true")
    return parser.parse_args()


class PlateDatabase:
    def __init__(self, db_path: str):
        self.plates = []
        self.load(db_path)

    @staticmethod
    def _normalize(plate: str) -> str:
        return re.sub(r"\s+", " ", str(plate).upper().strip())

    @staticmethod
    def _parts(plate: str):
        parts = PlateDatabase._normalize(plate).split()
        if len(parts) >= 3:
            return parts[0], parts[1], "".join(parts[2:])
        if len(parts) == 2:
            return parts[0], parts[1], ""
        return "", "", ""

    def load(self, db_path: str):
        path = Path(db_path)
        if not path.exists():
            print(f"[WARNING] Database tidak ditemukan: {db_path}")
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[ERROR] Gagal membaca database: {exc}")
            return

        for entry in data.get("registered_plates", []):
            if not entry.get("active", True) or not entry.get("plate"):
                continue
            normalized = self._normalize(entry["plate"])
            self.plates.append({
                **entry,
                "normalized": normalized,
                "parts": self._parts(normalized),
            })
        print(f"Database: {len(self.plates)} plat terdaftar dimuat")

    def match(self, ocr_text: str) -> dict | None:
        """Return a registered vehicle only for an exact normalized plate.

        Previous substring/digit-only matching could open the gate for an OCR
        result belonging to another vehicle. Access control must not use that
        kind of fuzzy match.
        """
        normalized = self._normalize(ocr_text)
        if not normalized:
            return None
        for entry in self.plates:
            if normalized == entry["normalized"]:
                return entry
            if self._parts(normalized) == entry["parts"]:
                return entry
        return None


class LaneGate:
    COLORS = {
        "gate_open": (0, 255, 0),
        "gate_closed": (0, 0, 255),
        "text": (255, 0, 0),
        "info": (255, 255, 0),
        "plate_match": (0, 255, 0),
        "plate_detect": (0, 165, 255),
    }
    STALE_LIMIT = 15
    TRACK_IOU_THRESHOLD = 0.25

    def __init__(self, lane_name: str, gate_duration: float):
        self.lane_name = lane_name
        self.gate_duration = gate_duration
        self.gate_open_until = 0.0
        self.last_match = None
        self.match_count = 0
        self.served_plates = set()
        self.log = []
        self.current_plate_text = ""
        self.current_match = None
        self.locked = False
        self.no_detect_count = 0
        self.last_bbox = None
        self.last_ocr_text = ""

    def reset(self, preserve_count: bool = False):
        self.gate_open_until = 0.0
        self.last_match = None
        if not preserve_count:
            self.match_count = 0
            self.served_plates.clear()
        self.current_plate_text = ""
        self.current_match = None
        self.locked = False
        self.no_detect_count = 0
        self.last_bbox = None
        self.last_ocr_text = ""

    @property
    def is_gate_open(self) -> bool:
        return time.time() < self.gate_open_until

    @staticmethod
    def _iou(a, b) -> float:
        if a is None or b is None:
            return 0.0
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
        inter = iw * ih
        area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
        area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
        union = area_a + area_b - inter
        return inter / union if union else 0.0

    def update_detection(self, bbox):
        self.no_detect_count = 0
        same_track = self._iou(self.last_bbox, bbox) >= self.TRACK_IOU_THRESHOLD
        self.last_bbox = tuple(bbox)
        return same_track

    def mark_no_detection(self):
        self.no_detect_count += 1
        if self.no_detect_count > self.STALE_LIMIT:
            # Vehicle has left. Unlock so the next vehicle can be served.
            self.current_plate_text = ""
            self.current_match = None
            self.locked = False
            self.last_bbox = None
            self.last_ocr_text = ""

    def check_plate(self, plate_text: str, db: PlateDatabase, frame_num: int):
        if not plate_text:
            return None
        self.current_plate_text = plate_text

        # While a vehicle is locked, never switch its identity to another OCR
        # result. The lock is released only after the vehicle disappears.
        if self.locked:
            return self.current_match

        match = db.match(plate_text)
        if not match:
            return None

        plate_key = match["normalized"]
        if plate_key in self.served_plates:
            return self.current_match

        self.current_match = match
        self.last_match = match
        self.locked = True
        self.served_plates.add(plate_key)
        self.gate_open_until = time.time() + self.gate_duration
        self.match_count += 1

        log_entry = {
            "frame": frame_num,
            "time": datetime.now().strftime("%H:%M:%S"),
            "lane": self.lane_name,
            "plate_ocr": plate_text,
            "plate_db": match["plate"],
            "owner": match.get("owner", ""),
            "status": "PALANG TERBUKA",
        }
        self.log.append(log_entry)
        print(f"[PALANG TERBUKA] {self.lane_name}: {match['plate']} - {match.get('owner', '')}")
        return match

    def draw(self, frame: np.ndarray, x_start: int, x_end: int, fps: float):
        h = frame.shape[0]
        mid = x_start + (x_end - x_start) // 2
        if self.is_gate_open and self.last_match:
            remaining = max(0, self.gate_open_until - time.time())
            overlay = frame.copy()
            cv2.rectangle(overlay, (x_start, 0), (x_end, 60), (0, 100, 0), -1)
            cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
            cv2.putText(frame, "PALANG TERBUKA", (mid - 120, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.COLORS["gate_open"], 2)
            cv2.putText(frame, f"{remaining:.0f}s", (mid - 30, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.COLORS["info"], 2)
            info = self.last_match
            cv2.putText(frame, f"Plat: {info['plate']}", (x_start + 10, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.COLORS["text"], 2)
            cv2.putText(frame, f"Pemilik: {info.get('owner', '')}", (x_start + 10, 130),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.COLORS["text"], 2)
        elif self.current_match:
            cv2.putText(frame, f"Plat: {self.current_match['plate']}", (x_start + 10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, self.COLORS["plate_match"], 2)
            cv2.putText(frame, f"Pemilik: {self.current_match.get('owner', '')}", (x_start + 10, 55),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, self.COLORS["plate_match"], 2)
        elif self.current_plate_text:
            cv2.putText(frame, f"Plat: {self.current_plate_text}", (x_start + 10, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, self.COLORS["plate_detect"], 1)

        lines = [f"Gate: {'TERBUKA' if self.is_gate_open else 'TERTUTUP'}",
                 f"Total: {self.match_count}", f"FPS: {fps:.1f}"]
        panel_h = len(lines) * 22 + 16
        y_start = h - panel_h - 10
        overlay = frame.copy()
        cv2.rectangle(overlay, (x_start + 5, y_start), (x_start + 225, h - 10), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        for i, line in enumerate(lines):
            color = self.COLORS["gate_open"] if "TERBUKA" in line else self.COLORS["text"]
            cv2.putText(frame, line, (x_start + 12, y_start + 18 + i * 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)


class DualLaneDetector:
    def __init__(self, model_path, confidence, device, imgsz, ocr_interval, gate_duration):
        self.pipeline = ALPRPipeline(
            detector_model_path=model_path,
            ocr_engine="paddleocr",
            detection_confidence_threshold=confidence,
            ocr_confidence_threshold=confidence,
            overall_confidence_threshold=confidence,
            device=device,
            debug=False,
        )
        self.ocr_left = self.pipeline.ocr
        self.ocr_right = PlateOCR(engine="paddleocr", confidence_threshold=confidence)
        self.ocr_interval = max(1, ocr_interval)
        self.ocr_counter = 0
        self.frame_count = 0
        self.fps_history = []
        self.lane_left = LaneGate("KIRI", gate_duration)
        self.lane_right = LaneGate("KANAN", gate_duration)

    def _assign_lane(self, det, width):
        x1, _, x2, _ = det.bbox
        center_x = (x1 + x2) / 2
        # Fixed 50/50 split avoids the old 60/40 bias. Hysteresis is replaced
        # by the lane-local bbox tracker, so a different vehicle cannot inherit
        # another lane's previous center.
        return self.lane_left if center_x < width / 2 else self.lane_right

    def _ocr_for(self, crop, ocr):
        if crop.size == 0:
            return ""
        try:
            return ocr.read(crop).text.strip()
        except Exception as exc:
            print(f"[WARNING] OCR gagal: {exc}")
            return ""

    def process_frame(self, frame: np.ndarray, db: PlateDatabase):
        self.frame_count += 1
        self.ocr_counter += 1
        h, w = frame.shape[:2]
        start = time.time()
        run_ocr = self.ocr_counter == 1 or self.ocr_counter % self.ocr_interval == 0
        detections = self.pipeline.detector.detect(frame)
        annotated = frame.copy()
        seen = {self.lane_left: False, self.lane_right: False}

        for det in detections:
            lane = self._assign_lane(det, w)
            x1, y1, x2, y2 = map(int, det.bbox)
            same_track = lane.update_detection((x1, y1, x2, y2))
            seen[lane] = True
            ocr = self.ocr_left if lane is self.lane_left else self.ocr_right
            crop = frame[max(0, y1):min(h, y2), max(0, x1):min(w, x2)].copy()

            # Never reuse OCR from a different track. If OCR is skipped, reuse
            # only the previous result for the same bbox track.
            if run_ocr:
                plate_text = self._ocr_for(crop, ocr)
                if plate_text:
                    lane.last_ocr_text = plate_text
            elif same_track:
                plate_text = lane.last_ocr_text
            else:
                plate_text = ""

            if plate_text:
                lane.check_plate(plate_text, db, self.frame_count)

            if lane.is_gate_open:
                color = lane.COLORS["gate_open"]
            elif lane.current_match:
                color = lane.COLORS["plate_match"]
            else:
                color = lane.COLORS["plate_detect"]
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            cv2.putText(annotated, plate_text or "[detect]", (x1, max(20, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        for lane in (self.lane_left, self.lane_right):
            if not seen[lane]:
                lane.mark_no_detection()

        elapsed = time.time() - start
        fps = 1.0 / elapsed if elapsed > 0 else 0.0
        self.fps_history.append(fps)
        self.fps_history = self.fps_history[-60:]
        avg_fps = sum(self.fps_history) / len(self.fps_history)
        mid_x = w // 2
        cv2.line(annotated, (mid_x, 0), (mid_x, h), (255, 255, 255), 2)
        cv2.putText(annotated, "KIRI", (10, h - 110), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(annotated, "KANAN", (mid_x + 10, h - 110), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        self.lane_left.draw(annotated, 0, mid_x, avg_fps)
        self.lane_right.draw(annotated, mid_x, w, avg_fps)
        return annotated

    def get_summary(self):
        avg_fps = sum(self.fps_history) / len(self.fps_history) if self.fps_history else 0
        return {"total_frames": self.frame_count, "gate_left": self.lane_left.match_count,
                "gate_right": self.lane_right.match_count, "avg_fps": avg_fps}


def save_gate_report(left_log, right_log, video_source, summary):
    Path("output").mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path("output") / f"gate_report_{ts}.txt"
    with path.open("w", encoding="utf-8") as f:
        f.write("LAPORAN GATE DETECTION DUAL LANE\n")
        f.write(f"Tanggal: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
        f.write(f"Video: {video_source}\nTotal Frame: {summary['total_frames']}\n")
        f.write(f"Palang Kiri: {summary['gate_left']} kali\nPalang Kanan: {summary['gate_right']} kali\n")
        f.write(f"FPS Rata-rata: {summary['avg_fps']:.1f}\n")
        for label, log in (("KIRI", left_log), ("KANAN", right_log)):
            if not log:
                continue
            f.write(f"\n{'=' * 60}\nLOG PALANG TERBUKA - JALUR {label}\n{'=' * 60}\n")
            for i, entry in enumerate(log, 1):
                f.write(f"\n#{i}\nWaktu: {entry['time']} (frame {entry['frame']})\n")
                f.write(f"OCR: {entry['plate_ocr']}\nDatabase: {entry['plate_db']}\nPemilik: {entry['owner']}\n")
    print(f"Laporan tersimpan: {path}")


def open_source(video_source):
    if isinstance(video_source, str):
        v_str = video_source.strip()
        v_lower = v_str.lower()
        if v_lower.startswith("rstp://"):
            video_source = "rtsp://" + v_str[7:]
        elif v_lower.startswith("rstps://"):
            video_source = "rtsps://" + v_str[8:]
        if str(video_source).lower().startswith(("rtsp://", "rtsps://")):
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;3000000"
    cap = cv2.VideoCapture(video_source)
    return cap if cap.isOpened() else None


def main():
    args = parse_args()
    if args.stream:
        v_str = args.stream.strip()
        if v_str.lower().startswith("rstp://"):
            v_str = "rtsp://" + v_str[7:]
        elif v_str.lower().startswith("rstps://"):
            v_str = "rtsps://" + v_str[8:]
        video_source, is_camera = v_str, True
    elif args.camera_id is not None:
        import sqlite3
        try:
            db_file = Path("parking.db")
            if not db_file.exists():
                db_file = Path(__file__).resolve().parent / "parking.db"
            conn = sqlite3.connect(str(db_file))
            row = conn.execute("SELECT url, name FROM camera_sources WHERE id = ?", (args.camera_id,)).fetchone()
            conn.close()
            if not row:
                print(f"[ERROR] Kamera dengan ID {args.camera_id} tidak ditemukan di database")
                sys.exit(1)
            video_source = row[0]
            if video_source.lower().startswith("rstp://"):
                video_source = "rtsp://" + video_source[7:]
            elif video_source.lower().startswith("rstps://"):
                video_source = "rtsps://" + video_source[8:]
            is_camera = True
            print(f"[INFO] Menggunakan kamera dari database: {row[1]} ({video_source})")
        except Exception as e:
            print(f"[ERROR] Gagal membaca database kamera: {e}")
            sys.exit(1)
    elif args.video:
        is_stream_url = args.video.lower().startswith(("rtsp://", "rtsps://", "rstp://", "rstps://", "http://", "https://"))
        if not is_stream_url and not Path(args.video).exists():
            print(f"[ERROR] Video tidak ditemukan: {args.video}")
            sys.exit(1)
        video_source, is_camera = args.video, is_stream_url

    elif args.camera is not None:
        video_source, is_camera = args.camera, True
    else:
        video_source, is_camera = 0, True

    db = PlateDatabase(args.db)
    print(f"Model: {args.model} | Device: {args.device}")
    detector = DualLaneDetector(args.model, args.conf, args.device, args.imgsz,
                                args.ocr_interval, args.gate_duration)
    cap = open_source(video_source)
    if cap is None:
        print(f"[ERROR] Tidak dapat membuka: {video_source}")
        sys.exit(1)

    writer = None
    paused = False
    try:
        while True:
            if paused:
                key = cv2.waitKey(0) & 0xFF
                if key in (ord("q"), 27): break
                if key == ord("p"): paused = False
                continue
            ret, frame = cap.read()
            if not ret:
                if not is_camera and args.loop:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                if is_camera:
                    cap.release(); time.sleep(2); cap = open_source(video_source)
                    if cap is None: break
                    continue
                break
            annotated = detector.process_frame(frame, db)
            if args.save:
                if writer is None:
                    h, w = annotated.shape[:2]
                    writer = cv2.VideoWriter(args.save, cv2.VideoWriter_fourcc(*"mp4v"),
                                             20.0, (w, h))
                writer.write(annotated)
            if not args.headless:
                cv2.imshow("Gate Detection - Dual Lane", annotated)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27): break
            if key == ord("p"): paused = True
            elif key == ord("r"):
                db = PlateDatabase(args.db)
                detector.lane_left.reset(preserve_count=True)
                detector.lane_right.reset(preserve_count=True)
            elif key in (ord("+"), ord("=")):
                value = min(1.0, detector.pipeline.detection_conf_threshold + 0.05)
                detector.pipeline.detection_conf_threshold = value
                detector.pipeline.ocr_conf_threshold = value
                detector.pipeline.overall_conf_threshold = value
            elif key == ord("-"):
                value = max(0.05, detector.pipeline.detection_conf_threshold - 0.05)
                detector.pipeline.detection_conf_threshold = value
                detector.pipeline.ocr_conf_threshold = value
                detector.pipeline.overall_conf_threshold = value
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        if writer: writer.release()
        if not args.headless: cv2.destroyAllWindows()

    summary = detector.get_summary()
    print("\n" + "=" * 50)
    print("RINGKASAN GATE DUAL LANE")
    print("=" * 50)
    print(f"Total frame   : {summary['total_frames']}")
    print(f"Palang KIRI   : {summary['gate_left']} kali")
    print(f"Palang KANAN  : {summary['gate_right']} kali")
    print(f"FPS rata-rata : {summary['avg_fps']:.1f}")
    print("=" * 50)
    logs = detector.lane_left.log + detector.lane_right.log
    if logs:
        save_gate_report(detector.lane_left.log, detector.lane_right.log, video_source, summary)


if __name__ == "__main__":
    main()
