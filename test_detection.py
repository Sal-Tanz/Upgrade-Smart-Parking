"""
Uji Coba YOLO Detection + OCR pada gambar di image/data_training/

Cara pakai:
    python test_detection.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from ml.alpr.pipeline import ALPRPipeline


def main():
    image_dir = Path("image/data_training")
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    image_files = sorted(image_dir.glob("*.jpg"))
    if not image_files:
        print(f"Tidak ada gambar ditemukan di {image_dir}")
        return

    print(f"Memuat model ALPR Pipeline...")
    pipeline = ALPRPipeline(
        detector_model_path="ml/models/yolov8_plate.pt",
        ocr_engine="paddleocr",
        detection_confidence_threshold=0.3,
        ocr_confidence_threshold=0.3,
        overall_confidence_threshold=0.3,
        device="cuda",
        debug=False,
    )
    print(f"Model siap. Memproses {len(image_files)} gambar...\n")

    results_text = []
    separator = "=" * 60

    for img_path in image_files:
        print(f"Memproses: {img_path.name}...")

        result = pipeline.process(str(img_path), return_images=False)

        status_icon = {
            "ACCEPTED": "[OK]",
            "REJECTED": "[--]",
            "RETRY": "[??]",
        }

        status = result.vehicle_status.value
        icon = status_icon.get(status, "[??]")

        entry = f"""{separator}
File: {img_path.name}
{icon} Status: {status}
Plat Nomor: {result.plate_text if result.plate_text else '(tidak terdeteksi)'}
Teks Mentah: {result.raw_plate_text if result.raw_plate_text else '(kosong)'}
Confidence Deteksi YOLO: {result.detection_confidence:.3f}
Confidence OCR: {result.ocr_confidence:.3f}
Confidence Keseluruhan: {result.overall_confidence:.3f}
Valid Format: {'Ya' if result.is_valid_format else 'Tidak'}
Engine OCR: {result.ocr_engine_used}
Bounding Box: {result.bbox}
Error: {result.error_message if result.error_message else '-'}
{separator}
"""
        results_text.append(entry)
        print(f"  -> Plat: {result.plate_text or '(tidak terdeteksi)'} | Status: {status}\n")

    # Simpan hasil ke file teks
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"hasil_deteksi_{timestamp}.txt"

    full_report = f"""LAPORAN HASIL DETEKSI PLAT NOMOR
Tanggal: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Jumlah Gambar: {len(image_files)}
Model YOLO: ml/models/yolov8_plate.pt

"""
    full_report += "\n".join(results_text)

    # Ringkasan
    total = len(results_text)
    accepted = sum(1 for r in results_text if "ACCEPTED" in r)
    rejected = sum(1 for r in results_text if "REJECTED" in r)
    retry = sum(1 for r in results_text if "[??" in r)

    full_report += f"""
RINGKASAN
{'=' * 60}
Total Gambar:     {total}
Terdeteksi:       {accepted}
Tidak Valid:      {rejected}
Perlu Retry:      {retry}
{'=' * 60}
"""

    output_file.write_text(full_report, encoding="utf-8")
    print(f"\nHasil tersimpan ke: {output_file}")
    print(f"\nRingkasan: {accepted} terdeteksi / {rejected} tidak valid / {retry} perlu retry dari {total} gambar")


if __name__ == "__main__":
    main()
