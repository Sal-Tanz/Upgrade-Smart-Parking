"""
Uji Coba YOLO Detection pada Video — Deteksi Plat Nomor dari Video.

Cara pakai:
    python test_video_detection.py --video path/to/video.mp4
    python test_video_detection.py --video video.mp4 --save output/result.mp4
    python test_video_detection.py --video video.mp4 --conf 0.05
    python test_video_detection.py --camera 0

Tombol keyboard:
    q / ESC  : Keluar
    s        : Screenshot frame
    p        : Pause / Resume
    +/-      : Adjust confidence threshold
"""

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from ml.alpr.detector import PlateDetector


def parse_args():
    parser = argparse.ArgumentParser(
        description="Uji YOLO deteksi plat nomor pada video"
    )

    source = parser.add_mutually_exclusive_group()
    source.add_argument("--video", type=str, default=None, help="Path ke file video")
    source.add_argument("--camera", type=int, default=None, help="Index kamera")

    parser.add_argument("--model", type=str, default="ml/models/best.pt",
                        help="Path ke model YOLOv8 (default: ml/models/best.pt)")
    parser.add_argument("--conf", type=float, default=0.10,
                        help="Confidence threshold (default: 0.10)")
    parser.add_argument("--iou", type=float, default=0.45,
                        help="IoU threshold untuk NMS (default: 0.45)")
    parser.add_argument("--device", type=str, default="cpu",
                        help="Device: cpu, cuda, cuda:0, mps (default: cpu)")
    parser.add_argument("--imgsz", type=int, default=640,
                        help="Ukuran input image untuk YOLO (default: 640)")
    parser.add_argument("--save", type=str, default=None,
                        help="Path untuk menyimpan video hasil deteksi")
    parser.add_argument("--headless", action="store_true",
                        help="Mode headless tanpa jendela tampilan")
    parser.add_argument("--skip-frames", type=int, default=0,
                        help="Skip N frame antar deteksi (0 = deteksi setiap frame)")

    return parser.parse_args()


class VideoDetector:
    """Deteksi plat nomor dari video stream menggunakan YOLOv8."""

    COLORS = {
        "high": (0, 255, 0),
        "mid": (0, 255, 255),
        "low": (0, 0, 255),
        "text": (255, 255, 255),
    }

    def __init__(self, model_path, confidence=0.10, iou=0.45, device="cpu", imgsz=640):
        self.detector = PlateDetector(
            model_path=model_path,
            confidence_threshold=confidence,
            iou_threshold=iou,
            device=device,
            imgsz=imgsz,
        )
        self.frame_count = 0
        self.detection_count = 0
        self.fps_history = []

    def process_frame(self, frame):
        self.frame_count += 1
        start = time.time()
        detections = self.detector.detect(frame)
        elapsed = time.time() - start
        fps = 1.0 / elapsed if elapsed > 0 else 0
        self.fps_history.append(fps)
        if len(self.fps_history) > 60:
            self.fps_history.pop(0)

        annotated = self.detector.draw_detections(frame, detections)
        self.detection_count += len(detections)
        self._draw_info_panel(annotated, fps, len(detections))
        return annotated, detections

    def _draw_info_panel(self, frame, fps, det_count):
        avg_fps = sum(self.fps_history) / len(self.fps_history) if self.fps_history else 0
        lines = [
            f"FPS: {avg_fps:.1f}",
            f"Frame: {self.frame_count}",
            f"Detections: {det_count} | Total: {self.detection_count}",
            f"Conf: {self.detector.confidence_threshold:.2f}",
        ]
        padding = 10
        line_height = 28
        panel_h = len(lines) * line_height + padding * 2
        panel_w = 320

        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (panel_w, panel_h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        for i, text in enumerate(lines):
            y = padding + (i + 1) * line_height - 5
            cv2.putText(frame, text, (padding, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.COLORS["text"], 2)

    def get_summary(self):
        avg_fps = sum(self.fps_history) / len(self.fps_history) if self.fps_history else 0
        return {
            "total_frames": self.frame_count,
            "total_detections": self.detection_count,
            "avg_fps": avg_fps,
            "confidence_threshold": self.detector.confidence_threshold,
        }


def main():
    args = parse_args()

    if args.video:
        if not Path(args.video).exists():
            print(f"[ERROR] File video tidak ditemukan: {args.video}")
            sys.exit(1)
        video_source = args.video
    elif args.camera is not None:
        video_source = args.camera
    else:
        video_source = 0

    print(f"Memuat model: {args.model}")
    print(f"Confidence: {args.conf} | IoU: {args.iou} | Device: {args.device}")

    try:
        vd = VideoDetector(
            model_path=args.model, confidence=args.conf, iou=args.iou,
            device=args.device, imgsz=args.imgsz,
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
    print(f"Video: {width}x{height} | {total_frames_vid} frames | {fps_vid:.1f} fps\n")

    writer = None
    if args.save:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(args.save, fourcc, fps_vid or 30.0, (width, height))
        if not writer.isOpened():
            print(f"[ERROR] Gagal membuat video writer: {args.save}")
            writer = None
        else:
            print(f"Video output: {args.save}")

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
                    continue

                annotated, detections = vd.process_frame(frame)
                if writer:
                    writer.write(annotated)

            if not args.headless:
                display = annotated if not paused else frame
                cv2.imshow("YOLO Plate Detection", display)

            key = cv2.waitKey(1 if not paused else 0) & 0xFF
            if key in (ord("q"), 27):
                print("\nDihentikan oleh user.")
                break
            elif key == ord("p"):
                paused = not paused
                print(f"[{'PAUSED' if paused else 'RESUME'}]")
            elif key == ord("s"):
                Path("output/screenshots").mkdir(parents=True, exist_ok=True)
                path = f"output/screenshots/frame_{vd.frame_count:06d}.jpg"
                cv2.imwrite(path, annotated)
                print(f"Screenshot: {path}")
            elif key in (ord("+"), ord("=")):
                vd.detector.confidence_threshold = min(1.0, vd.detector.confidence_threshold + 0.05)
                print(f"Confidence: {vd.detector.confidence_threshold:.2f}")
            elif key == ord("-"):
                vd.detector.confidence_threshold = max(0.01, vd.detector.confidence_threshold - 0.05)
                print(f"Confidence: {vd.detector.confidence_threshold:.2f}")

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
    print("RINGKASAN DETEKSI VIDEO")
    print("=" * 50)
    print(f"Total frame diproses : {summary['total_frames']}")
    print(f"Total deteksi plat   : {summary['total_detections']}")
    print(f"Rata-rata FPS        : {summary['avg_fps']:.1f}")
    print(f"Confidence threshold  : {summary['confidence_threshold']:.2f}")
    print("=" * 50)
    if args.save:
        print(f"Video tersimpan: {args.save}")


if __name__ == "__main__":
    main()
