"""
Uji Coba YOLO Detection + OCR pada Video — Deteksi & Baca Plat Nomor dari Video.

Program ini membaca video (file atau kamera), menjalankan deteksi plat nomor
YOLOv8 + OCR PaddleOCR frame-by-frame, dan menampilkan hasilnya secara real-time.

Cara pakai:
    # Deteksi dari file video
    python test_yolo-ocr_detection_video.py --video path/to/video.mp4

    # Deteksi dari kamera (default 0)
    python test_yolo-ocr_detection_video.py --camera 0

    # Simpan video hasil deteksi
    python test_yolo-ocr_detection_video.py --video video.mp4 --save output/result.mp4

    # Adjust confidence threshold
    python test_yolo-ocr_detection_video.py --video video.mp4 --conf 0.3

    # OCR hanya setiap 5 frame (lebih cepat, FPS tinggi)
    python test_yolo-ocr_detection_video.py --video video.mp4 --ocr-interval 5

    # Mode headless (tanpa tampilan window, untuk server)
    python test_yolo-ocr_detection_video.py --video video.mp4 --headless --save output/result.mp4

Tombol keyboard (mode tampilan):
    q / ESC  : Keluar
    s        : Screenshot frame saat ini
    p        : Pause / Resume
    +/-      : Adjust confidence threshold
"""

import argparse
import sys
import time
from pathlib import Path
from datetime import datetime

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from ml.alpr.pipeline import ALPRPipeline


def parse_args():
    parser = argparse.ArgumentParser(
        description="Uji YOLO + OCR deteksi plat nomor pada video"
    )

    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--video",
        type=str,
        default=None,
        help="Path ke file video (mp4, avi, mkv, dll)",
    )
    source.add_argument(
        "--camera",
        type=int,
        default=None,
        help="Index kamera (default: 0 jika --video tidak diisi)",
    )

    parser.add_argument(
        "--model",
        type=str,
        default="ml/models/best.pt",
        help="Path ke model YOLOv8 terlatih (default: ml/models/best.pt)",
    )
    parser.add_argument(
        "--conf", type=float, default=0.25, help="Confidence threshold (default: 0.25)"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda",
        help="Device: cpu, cuda, cuda:0, mps (default: cuda)",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=416,
        help="Ukuran input image untuk YOLO (default: 416)",
    )
    parser.add_argument(
        "--save",
        type=str,
        default=None,
        help="Path untuk menyimpan video hasil deteksi (default: tidak disimpan)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Mode headless tanpa jendela tampilan (untuk server/CI)",
    )
    parser.add_argument(
        "--skip-frames",
        type=int,
        default=0,
        help="Skip N frame antar deteksi (0 = deteksi setiap frame)",
    )
    parser.add_argument(
        "--ocr-interval",
        type=int,
        default=0,
        help="OCR hanya setiap N frame, frame lain hanya YOLO (0 = setiap frame). "
             "Contoh: 5 = OCR setiap 5 frame, FPS naik signifikan.",
    )

    return parser.parse_args()


class ALPRVideoDetector:
    """Deteksi plat nomor + OCR dari video stream menggunakan YOLOv8 + PaddleOCR."""

    COLORS = {
        "high": (0, 255, 0),
        "mid": (0, 255, 255),
        "low": (0, 0, 255),
        "bg": (0, 0, 0),
        "text": (255, 255, 255),
    }

    STATUS_COLORS = {
        "ACCEPTED": (0, 255, 0),
        "RETRY": (0, 255, 255),
        "REJECTED": (0, 0, 255),
    }

    def __init__(
        self,
        model_path: str,
        confidence: float = 0.5,
        device: str = "cuda",
        imgsz: int = 416,
        ocr_interval: int = 0,
    ):
        self.pipeline = ALPRPipeline(
            detector_model_path=model_path,
            ocr_engine="paddleocr",
            detection_confidence_threshold=confidence,
            ocr_confidence_threshold=confidence,
            overall_confidence_threshold=confidence,
            device=device,
            debug=False,
        )
        self.frame_count = 0
        self.detection_count = 0
        self.ocr_count = 0
        self.fps_history = []
        self.results_log = []
        self.ocr_interval = ocr_interval
        self.ocr_counter = 0
        self.last_result = None

    def process_frame(self, frame: np.ndarray) -> tuple[np.ndarray, object]:
        """Proses satu frame: deteksi plat + OCR (jika interval cocok)."""
        self.frame_count += 1
        self.ocr_counter += 1

        start = time.time()

        run_ocr = (self.ocr_interval <= 0) or (self.ocr_counter % self.ocr_interval == 1)

        if run_ocr:
            result = self.pipeline.process_video_frame(frame)
            self.last_result = result
        else:
            det = self.pipeline.detector.detect_best_plate(frame)
            if det is not None and self.last_result is not None:
                from ml.alpr.pipeline import ALPRResult
                result = ALPRResult(
                    plate_text=self.last_result.plate_text,
                    raw_plate_text=self.last_result.raw_plate_text,
                    detection_confidence=det.confidence,
                    ocr_confidence=self.last_result.ocr_confidence,
                    overall_confidence=self.last_result.overall_confidence,
                    bbox=det.bbox,
                    vehicle_status=self.last_result.vehicle_status,
                    is_valid_format=self.last_result.is_valid_format,
                    ocr_engine_used=self.last_result.ocr_engine_used,
                    processing_time_ms=0.0,
                    cropped_plate=det.cropped_image,
                )
            elif det is not None:
                from ml.alpr.pipeline import ALPRResult, VehicleStatus
                result = ALPRResult(
                    plate_text="",
                    raw_plate_text="",
                    detection_confidence=det.confidence,
                    ocr_confidence=0.0,
                    overall_confidence=0.0,
                    bbox=det.bbox,
                    vehicle_status=VehicleStatus.REJECTED,
                    is_valid_format=False,
                    ocr_engine_used="",
                )
            else:
                result = self.pipeline._create_no_detection_result(frame, False)

        elapsed = time.time() - start
        fps = 1.0 / elapsed if elapsed > 0 else 0
        self.fps_history.append(fps)
        if len(self.fps_history) > 60:
            self.fps_history.pop(0)

        annotated = frame.copy()

        if result.bbox:
            self.detection_count += 1
            if result.plate_text:
                self.ocr_count += 1

            x1, y1, x2, y2 = result.bbox
            status = result.vehicle_status.value
            color = self.STATUS_COLORS.get(status, (0, 0, 255))

            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            label = f"{result.plate_text} [{status}]" if result.plate_text else f"[{status}]"
            (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            cv2.rectangle(annotated, (x1, y1 - label_h - 10), (x1 + label_w + 10, y1), color, -1)
            cv2.putText(annotated, label, (x1 + 5, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        self.results_log.append({
            "frame": self.frame_count,
            "plate_text": result.plate_text or "",
            "raw_text": result.raw_plate_text or "",
            "status": result.vehicle_status.value,
            "det_conf": result.detection_confidence,
            "ocr_conf": result.ocr_confidence,
            "overall_conf": result.overall_confidence,
            "valid_format": result.is_valid_format,
            "bbox": result.bbox,
            "error": result.error_message or "",
            "fps": fps,
        })

        self._draw_info_panel(annotated, fps, result)

        return annotated, result

    def _draw_info_panel(self, frame: np.ndarray, fps: float, result):
        """Gambar panel informasi di pojok kiri atas."""
        h, w = frame.shape[:2]
        avg_fps = sum(self.fps_history) / len(self.fps_history) if self.fps_history else 0

        plate_text = result.plate_text if result.plate_text else "-"
        det_conf = f"{result.detection_confidence:.2f}" if result.bbox else "-"
        ocr_conf = f"{result.ocr_confidence:.2f}" if result.plate_text else "-"

        lines = [
            f"FPS: {avg_fps:.1f}",
            f"Frame: {self.frame_count}",
            f"Deteksi: {self.detection_count} | OCR: {self.ocr_count}",
            f"Plat: {plate_text}",
            f"YOLO Conf: {det_conf} | OCR Conf: {ocr_conf}",
            f"Threshold: {self.pipeline.detection_conf_threshold:.2f}",
        ]
        if self.ocr_interval > 0:
            lines.append(f"OCR Interval: {self.ocr_interval} frame")

        padding = 10
        line_height = 28
        panel_h = len(lines) * line_height + padding * 2
        panel_w = 380

        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (panel_w, panel_h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        for i, text in enumerate(lines):
            y = padding + (i + 1) * line_height - 5
            cv2.putText(frame, text, (padding, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.COLORS["text"], 2)

    def get_summary(self) -> dict:
        avg_fps = sum(self.fps_history) / len(self.fps_history) if self.fps_history else 0
        return {
            "total_frames": self.frame_count,
            "total_detections": self.detection_count,
            "total_ocr": self.ocr_count,
            "avg_fps": avg_fps,
            "confidence_threshold": self.pipeline.detection_conf_threshold,
        }


def create_video_writer(
    video_path: str, cap: cv2.VideoCapture, output_path: str
) -> cv2.VideoWriter | None:
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
    if not out.isOpened():
        print(f"[ERROR] Gagal membuat video writer: {output_path}")
        return None

    print(f"Video output: {output_path} ({w}x{h} @ {fps:.1f} fps)")
    return out


def save_screenshot(frame: np.ndarray, frame_num: int):
    Path("output/screenshots").mkdir(parents=True, exist_ok=True)
    path = f"output/screenshots/frame_{frame_num:06d}.jpg"
    cv2.imwrite(path, frame)
    print(f"Screenshot tersimpan: {path}")


def save_report(results_log: list, video_source, model_path: str, total_frames_vid: int, skip_frames: int):
    """Simpan laporan hasil deteksi ke file teks."""
    Path("output").mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = f"output/hasil_deteksi_video_{ts}.txt"

    with open(report_path, "w") as f:
        f.write("LAPORAN HASIL DETEKSI PLAT NOMOR DARI VIDEO\n")
        f.write(f"Tanggal: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"File Video: {video_source}\n")
        f.write(f"Total Frame: {total_frames_vid}\n")
        f.write(f"Frame Diproses: {len(results_log)}")
        if skip_frames > 0:
            f.write(f" (setiap {skip_frames + 1} frame)")
        f.write("\n")
        f.write(f"Model YOLO: {model_path}\n")
        f.write("\n")

        for r in results_log:
            f.write("=" * 60 + "\n")
            f.write(f"Frame: {r['frame']} (waktu: {1.0 / r['fps']:.2f}s)\n")
            f.write(f"[{r['status']}] Status: {r['status']}\n")
            if r["plate_text"]:
                f.write(f"Plat Nomor: {r['plate_text']}\n")
                f.write(f"Teks Mentah: {r['raw_text']}\n")
            else:
                f.write(f"Plat Nomor: (tidak terdeteksi)\n")
                f.write(f"Teks Mentah: (kosong)\n")
            f.write(f"Confidence Deteksi YOLO: {r['det_conf']:.3f}\n")
            f.write(f"Confidence OCR: {r['ocr_conf']:.3f}\n")
            f.write(f"Confidence Keseluruhan: {r['overall_conf']:.3f}\n")
            f.write(f"Valid Format: {'Ya' if r['valid_format'] else 'Tidak'}\n")
            if r["bbox"]:
                f.write(f"Bounding Box: {r['bbox']}\n")
            if r["error"]:
                f.write(f"Error: {r['error']}\n")
            f.write("=" * 60 + "\n\n")

        # Summary
        detections = [r for r in results_log if r["plate_text"]]
        accepted = [r for r in results_log if r["status"] == "ACCEPTED"]
        plates = sorted(set(r["plate_text"] for r in detections if r["plate_text"]))

        f.write("\n" + "=" * 60 + "\n")
        f.write("RINGKASAN\n")
        f.write("=" * 60 + "\n")
        f.write(f"Total frame diproses : {len(results_log)}\n")
        f.write(f"Total deteksi plat   : {len(detections)}\n")
        f.write(f"Total ACCEPTED       : {len(accepted)}\n")
        f.write(f"Plat unik ditemukan  : {', '.join(plates) if plates else '-'}\n")
        f.write("=" * 60 + "\n")

    print(f"Laporan tersimpan: {report_path}")
    return report_path


def main():
    args = parse_args()

    if args.video:
        video_source = args.video
        if not Path(video_source).exists():
            print(f"[ERROR] File video tidak ditemukan: {video_source}")
            sys.exit(1)
    elif args.camera is not None:
        video_source = args.camera
    else:
        video_source = 0

    print(f"Memuat model: {args.model}")
    print(f"Confidence: {args.conf} | Device: {args.device} | ImgSz: {args.imgsz}")
    if args.ocr_interval > 0:
        print(f"OCR Interval: setiap {args.ocr_interval} frame")

    try:
        vd = ALPRVideoDetector(
            model_path=args.model,
            confidence=args.conf,
            device=args.device,
            imgsz=args.imgsz,
            ocr_interval=args.ocr_interval,
        )
    except Exception as e:
        print(f"[ERROR] Gagal memuat model: {e}")
        sys.exit(1)

    print(f"Model siap. Membuka video: {video_source}")

    cap = cv2.VideoCapture(video_source)
    if not cap.isOpened():
        print(f"[ERROR] Tidak dapat membuka video: {video_source}")
        sys.exit(1)

    total_frames_vid = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps_vid = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"Video: {width}x{height} | {total_frames_vid} frames | {fps_vid:.1f} fps")
    print()

    writer = None
    if args.save:
        Path(args.save).parent.mkdir(parents=True, exist_ok=True)
        writer = create_video_writer(str(video_source), cap, args.save)

    paused = False
    skip_counter = 0

    try:
        while True:
            if not paused:
                ret, frame = cap.read()
                if not ret:
                    break

                skip_counter += 1
                if args.skip_frames > 0 and skip_counter % (args.skip_frames + 1) != 0:
                    if writer:
                        writer.write(frame)
                    if not args.headless:
                        display = frame.copy()
                        cv2.putText(display, "SKIPPED", (10, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                        cv2.imshow("ALPR Video Detection", display)
                    continue

                annotated, result = vd.process_frame(frame)

                if writer:
                    writer.write(annotated)

            if not args.headless:
                cv2.imshow("ALPR Video Detection", annotated if not paused else frame)

            key = cv2.waitKey(1 if not paused else 0) & 0xFF

            if key in (ord("q"), 27):
                print("\nDihentikan oleh user.")
                break
            elif key == ord("p"):
                paused = not paused
                print(f"[{'PAUSED' if paused else 'RESUME'}]")
            elif key == ord("s"):
                save_screenshot(annotated, vd.frame_count)
            elif key in (ord("+"), ord("=")):
                vd.pipeline.detection_conf_threshold = min(1.0, vd.pipeline.detection_conf_threshold + 0.05)
                vd.pipeline.ocr_conf_threshold = vd.pipeline.detection_conf_threshold
                vd.pipeline.overall_conf_threshold = vd.pipeline.detection_conf_threshold
                print(f"Confidence: {vd.pipeline.detection_conf_threshold:.2f}")
            elif key == ord("-"):
                vd.pipeline.detection_conf_threshold = max(0.05, vd.pipeline.detection_conf_threshold - 0.05)
                vd.pipeline.ocr_conf_threshold = vd.pipeline.detection_conf_threshold
                vd.pipeline.overall_conf_threshold = vd.pipeline.detection_conf_threshold
                print(f"Confidence: {vd.pipeline.detection_conf_threshold:.2f}")

    except KeyboardInterrupt:
        print("\nDihentikan (Ctrl+C).")
    finally:
        cap.release()
        if writer:
            writer.release()
        if not args.headless:
            cv2.destroyAllWindows()

    summary = vd.get_summary()
    print()
    print("=" * 50)
    print("RINGKASAN DETEKSI VIDEO (YOLO + OCR)")
    print("=" * 50)
    print(f"Total frame diproses : {summary['total_frames']}")
    print(f"Total deteksi plat   : {summary['total_detections']}")
    print(f"Total terbaca (OCR)  : {summary['total_ocr']}")
    print(f"Rata-rata FPS        : {summary['avg_fps']:.1f}")
    print(f"Confidence threshold  : {summary['confidence_threshold']:.2f}")
    if args.ocr_interval > 0:
        print(f"OCR Interval         : {args.ocr_interval} frame")
    print("=" * 50)

    if args.save:
        print(f"Video tersimpan: {args.save}")

    if vd.results_log:
        save_report(vd.results_log, video_source, args.model, total_frames_vid, args.skip_frames)


if __name__ == "__main__":
    main()
