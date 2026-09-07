"""Detection endpoints — ALPR pipeline (YOLO + PaddleOCR)."""
import asyncio

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.schemas.detection import (
    DetectionListResponse,
    DetectionResponse,
    DetectionResult,
    DetectionValidation,
)
from api.services.event_service import EventService
from api.services.parking_service import ParkingService
from api.services.validation_service import ValidationService
from api.services.vehicle_service import VehicleService
from ml.alpr.pipeline import ALPRPipeline, VehicleStatus

router = APIRouter(prefix="/api", tags=["detection"])

# Lazy-init pipeline (avoid loading ML models at import time)
_pipeline: ALPRPipeline | None = None


def _get_pipeline() -> ALPRPipeline:
    global _pipeline
    if _pipeline is None:
        try:
            _pipeline = ALPRPipeline()
        except ImportError as exc:
            raise HTTPException(
                status_code=503,
                detail=f"OCR engine belum terpasang di server: {exc}",
            ) from exc
    return _pipeline



vehicle_svc = VehicleService()
parking_svc = ParkingService("data/slot_config.json")
validation_svc = ValidationService(vehicle_svc, parking_svc)
event_svc = EventService()


def _decode_image(file_bytes: bytes) -> np.ndarray:
    """Decode image bytes to OpenCV BGR numpy array."""
    nparr = np.frombuffer(file_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="File bukan gambar yang valid")
    return image


def _run_pipeline(image: np.ndarray) -> "ALPRResult":
    """Run ALPR pipeline in sync context (called from thread pool)."""
    pipeline = _get_pipeline()
    return pipeline.process(image, return_images=False)


@router.post("/detect", response_model=DetectionResponse)
async def detect_plate(
    file: UploadFile = File(..., description="Gambar plat nomor (jpg/png)"),
    validate: bool = Query(False, description="Validasi plat terhadap database"),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload gambar → YOLO deteksi plat → PaddleOCR baca teks.

    Pipeline:
        1. YOLOv8 mendeteksi bounding box plat nomor
    2. Crop & preprocess gambar plat
        3. PaddleOCR membaca teks dari gambar plat
        4. Post-processing & validasi format plat Indonesia

    Args:
        file: File gambar (multipart/form-data)
        validate: Jika true, plat juga divalidasi terhadap database kendaraan
    """
    # Baca file bytes
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="File kosong")

    # Decode gambar
    image = _decode_image(contents)

    # Run ALPR pipeline (sync → thread pool agar tidak block event loop)
    result = await asyncio.to_thread(_run_pipeline, image)

    # Build response
    detection = DetectionResult(
        plate_text=result.plate_text,
        raw_plate_text=result.raw_plate_text,
        detection_confidence=round(result.detection_confidence, 4),
        ocr_confidence=round(result.ocr_confidence, 4),
        overall_confidence=round(result.overall_confidence, 4),
        bbox=list(result.bbox) if result.bbox else None,
        vehicle_status=result.vehicle_status.value,
        is_valid_format=result.is_valid_format,
        ocr_engine_used=result.ocr_engine_used,
        error_message=result.error_message,
    )

    validation = None

    # Optional: validasi plat terhadap database
    if validate and result.plate_text.strip():
        plate_text = result.plate_text.strip().upper()
        validation_svc_inst = ValidationService(vehicle_svc, parking_svc)
        plate_result = await validation_svc_inst.validate_plate(db, plate_text)

        validation = DetectionValidation(**plate_result)

        # Log event
        await event_svc.log_event(
            db,
            plate_number=plate_text,
            event_type=detection.vehicle_status,
            cluster=plate_result.get("cluster"),
            jabatan=plate_result.get("jabatan"),
            validation_result=plate_result.get("status"),
            confidence_score=result.overall_confidence,
            buzzer_pattern=plate_result.get("buzzer_pattern"),
        )

    return DetectionResponse(detection=detection, validation=validation)


@router.post("/detect/batch", response_model=DetectionListResponse)
async def detect_plates_batch(
    files: list[UploadFile] = File(..., description="Multi-upload gambar plat"),
    validate: bool = Query(False, description="Validasi plat terhadap database"),
    db: AsyncSession = Depends(get_db),
):
    """Batch detection: upload beberapa gambar sekaligus."""
    results = []

    for file in files:
        contents = await file.read()
        if not contents:
            continue

        try:
            image = _decode_image(contents)
        except HTTPException:
            continue

        result = await asyncio.to_thread(_run_pipeline, image)

        detection = DetectionResult(
            plate_text=result.plate_text,
            raw_plate_text=result.raw_plate_text,
            detection_confidence=round(result.detection_confidence, 4),
            ocr_confidence=round(result.ocr_confidence, 4),
            overall_confidence=round(result.overall_confidence, 4),
            bbox=list(result.bbox) if result.bbox else None,
            vehicle_status=result.vehicle_status.value,
            is_valid_format=result.is_valid_format,
            ocr_engine_used=result.ocr_engine_used,
            error_message=result.error_message,
        )

        validation = None
        if validate and result.plate_text.strip():
            plate_text = result.plate_text.strip().upper()
            validation_svc_inst = ValidationService(vehicle_svc, parking_svc)
            plate_result = await validation_svc_inst.validate_plate(db, plate_text)
            validation = DetectionValidation(**plate_result)

            await event_svc.log_event(
                db,
                plate_number=plate_text,
                event_type=detection.vehicle_status,
                cluster=plate_result.get("cluster"),
                jabatan=plate_result.get("jabatan"),
                validation_result=plate_result.get("status"),
                confidence_score=result.overall_confidence,
                buzzer_pattern=plate_result.get("buzzer_pattern"),
            )

        results.append(DetectionResponse(detection=detection, validation=validation))

    return DetectionListResponse(results=results, total=len(results))
