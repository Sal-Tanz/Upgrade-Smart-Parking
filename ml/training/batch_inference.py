"""
Batch Inference ALPR — Uji pipeline deteksi plat nomor pada dataset.

Alur:
1. Load ALPR pipeline (YOLOv8 plate detector + preprocessor + OCR)
2. Loop semua gambar di dataset
3. Simpan hasil (plate text, confidence, status) ke CSV + JSON
4. Simpan gambar dengan bounding box annotated
5. Tampilkan ringkasan statistik

Penggunaan:
    python -m ml.training.batch_inference
    python -m ml.training.batch_inference --source image/data_set --output output/batch_test
    python -m ml.training.batch_inference --model ml/models/best.pt --device cuda
"""

import argparse
import csv
import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

import cv2
import numpy as np
from loguru import logger
from tqdm import tqdm


@dataclass
class BatchResult:
    image_name: str
    image_path: str
    image_width: int
    image_height: int
    plate_detected: bool
    plate_text: str = ""
    raw_plate_text: str = ""
    detection_confidence: float = 0.0
    ocr_confidence: float = 0.0
    overall_confidence: float = 0.0
    is_valid_format: bool = False
    vehicle_status: str = "REJECTED"
    ocr_engine_used: str = ""
    inference_time_ms: float = 0.0
    error_message: str = ""


@dataclass
class BatchSummary:
    total_images: int = 0
    plates_detected: int = 0
    plates_accepted: int = 0
    plates_not_detected: int = 0
    plates_error: int = 0
    avg_detection_conf: float = 0.0
    avg_ocr_conf: float = 0.0
    avg_inference_time_ms: float = 0.0
    valid_format_count: int = 0
    detection_rate: float = 0.0
    acceptance_rate: float = 0.0
    results: list = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("results", None)
        return d


def run_batch_inference(
    source_dir: str = "image/data_set",
    output_dir: str = "output/batch_test",
    model_path: str = "ml/models/yolov8_plate.pt",
    ocr_engine: str = "paddleocr",
    confidence_threshold: float = 0.5,
    device: str = "cpu",
    max_images: int = None,
    save_annotated: bool = True,
    save_no_detection: bool = False,
) -> BatchSummary:
    source_path = Path(source_dir)
    output_path = Path(output_dir)

    if not source_path.exists():
        logger.error(f"Source directory not found: {source_dir}")
        return BatchSummary()

    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "annotated").mkdir(exist_ok=True)

    # Collect images
    image_exts = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
    image_files = sorted(
        [f for f in source_path.iterdir() if f.suffix.lower() in image_exts]
    )

    if max_images:
        image_files = image_files[:max_images]

    if not image_files:
        logger.error(f"No images found in {source_dir}")
        return BatchSummary()

    logger.info(f"Found {len(image_files)} images in {source_dir}")
    logger.info(f"Output: {output_path}")
    logger.info(f"Model: {model_path}")

    # Initialize ALPR pipeline
    try:
        from ml.alpr.pipeline import ALPRPipeline
        pipeline = ALPRPipeline(
            detector_model_path=model_path,
            ocr_engine=ocr_engine,
            detection_confidence_threshold=confidence_threshold,
            device=device,
            debug=False,
        )
    except Exception as e:
        logger.error(f"Failed to initialize ALPR pipeline: {e}")
        return BatchSummary()

    # Process each image
    results = []
    total_inference_time = 0.0
    detection_confs = []
    ocr_confs = []

    for img_file in tqdm(image_files, desc="Processing images"):
        result = BatchResult(
            image_name=img_file.name,
            image_path=str(img_file),
            image_width=0,
            image_height=0,
            plate_detected=False,
        )

        try:
            img = cv2.imread(str(img_file))
            if img is None:
                result.error_message = "Failed to read image"
                results.append(result)
                continue

            result.image_height, result.image_width = img.shape[:2]

            start_time = time.time()
            alpr_result = pipeline.process(img, return_images=save_annotated)
            elapsed_ms = (time.time() - start_time) * 1000

            result.inference_time_ms = elapsed_ms
            total_inference_time += elapsed_ms

            if alpr_result.vehicle_status.value == "REJECTED" and not alpr_result.plate_text:
                result.error_message = alpr_result.error_message or "No plate detected"
                results.append(result)
                continue

            result.plate_detected = True
            result.plate_text = alpr_result.plate_text
            result.raw_plate_text = alpr_result.raw_plate_text
            result.detection_confidence = alpr_result.detection_confidence
            result.ocr_confidence = alpr_result.ocr_confidence
            result.overall_confidence = alpr_result.overall_confidence
            result.is_valid_format = alpr_result.is_valid_format
            result.vehicle_status = alpr_result.vehicle_status.value
            result.ocr_engine_used = alpr_result.ocr_engine_used

            detection_confs.append(alpr_result.detection_confidence)
            ocr_confs.append(alpr_result.ocr_confidence)

            # Save annotated image
            if save_annotated and alpr_result.annotated_image is not None:
                ann_path = output_path / "annotated" / img_file.name
                cv2.imwrite(str(ann_path), alpr_result.annotated_image)

        except Exception as e:
            result.error_message = str(e)

        results.append(result)

    # Build summary
    total = len(results)
    detected = sum(1 for r in results if r.plate_detected)
    accepted = sum(1 for r in results if r.vehicle_status == "ACCEPTED")
    not_detected = sum(1 for r in results if not r.plate_detected and not r.error_message)
    errors = sum(1 for r in results if r.error_message)
    valid_format = sum(1 for r in results if r.is_valid_format)

    summary = BatchSummary(
        total_images=total,
        plates_detected=detected,
        plates_accepted=accepted,
        plates_not_detected=not_detected,
        plates_error=errors,
        avg_detection_conf=float(np.mean(detection_confs)) if detection_confs else 0.0,
        avg_ocr_conf=float(np.mean(ocr_confs)) if ocr_confs else 0.0,
        avg_inference_time_ms=total_inference_time / total if total > 0 else 0.0,
        valid_format_count=valid_format,
        detection_rate=detected / total if total > 0 else 0.0,
        acceptance_rate=accepted / total if total > 0 else 0.0,
        results=[asdict(r) for r in results],
    )

    return summary


def save_results(summary: BatchSummary, output_dir: str):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Save JSON
    json_path = output_path / "results.json"
    json_data = {
        "summary": summary.to_dict(),
        "results": summary.results,
    }
    json_path.write_text(json.dumps(json_data, indent=2))
    logger.info(f"JSON results saved: {json_path}")

    # Save CSV
    csv_path = output_path / "results.csv"
    if summary.results:
        fieldnames = list(summary.results[0].keys())
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(summary.results)
        logger.info(f"CSV results saved: {csv_path}")

    # Save summary report
    report_path = output_path / "report.txt"
    lines = [
        "=" * 60,
        "BATCH INFERENCE REPORT — ALPR Pipeline",
        "=" * 60,
        "",
        f"Total images:          {summary.total_images}",
        f"Plates detected:       {summary.plates_detected} ({summary.detection_rate:.1%})",
        f"Plates accepted:       {summary.plates_accepted} ({summary.acceptance_rate:.1%})",
        f"Plates NOT detected:   {summary.plates_not_detected}",
        f"Errors:                {summary.plates_error}",
        f"Valid format count:    {summary.valid_format_count}",
        "",
        f"Avg detection conf:    {summary.avg_detection_conf:.3f}",
        f"Avg OCR conf:          {summary.avg_ocr_conf:.3f}",
        f"Avg inference time:    {summary.avg_inference_time_ms:.1f} ms",
        "",
        "-" * 60,
        "RINGKASAN",
        "-" * 60,
    ]

    if summary.detection_rate >= 0.85:
        lines.append("✅ Detection rate >= 85% — OK")
    else:
        lines.append("⚠️ Detection rate < 85% — perlu improve dataset/model")

    if summary.acceptance_rate >= 0.70:
        lines.append("✅ Acceptance rate >= 70% — OK")
    else:
        lines.append("⚠️ Acceptance rate < 70% — perlu improve OCR/post-processing")

    lines.extend([
        "",
        "Files:",
        f"  Annotated images: {output_path / 'annotated/'}",
        f"  Results JSON:     {json_path}",
        f"  Results CSV:      {csv_path}",
        "",
        "=" * 60,
    ])

    report_path.write_text("\n".join(lines))
    logger.info(f"Report saved: {report_path}")

    # Print to console
    print("\n".join(lines))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch inference ALPR pada dataset")
    parser.add_argument("--source", default="image/data_set",
                        help="Direktori gambar (default: image/data_set)")
    parser.add_argument("--output", default="output/batch_test",
                        help="Direktori output (default: output/batch_test)")
    parser.add_argument("--model", default="ml/models/yolov8_plate.pt",
                        help="Path ke model YOLOv8 (default: ml/models/yolov8_plate.pt)")
    parser.add_argument("--ocr-engine", default="paddleocr",
                        help="Engine OCR: paddleocr atau easyocr (default: paddleocr)")
    parser.add_argument("--conf", type=float, default=0.5,
                        help="Confidence threshold (default: 0.5)")
    parser.add_argument("--device", default="cpu",
                        help="Device: cpu, cuda:0, mps (default: cpu)")
    parser.add_argument("--max-images", type=int, default=None,
                        help="Batasi jumlah gambar (default: semua)")
    parser.add_argument("--no-annotated", action="store_true",
                        help="Jangan simpan gambar annotated")

    args = parser.parse_args()

    summary = run_batch_inference(
        source_dir=args.source,
        output_dir=args.output,
        model_path=args.model,
        ocr_engine=args.ocr_engine,
        confidence_threshold=args.conf,
        device=args.device,
        max_images=args.max_images,
        save_annotated=not args.no_annotated,
    )

    if summary.total_images > 0:
        save_results(summary, args.output)
    else:
        logger.error("Batch inference gagal — tidak ada hasil")
