"""Camera management and streaming endpoints."""
import asyncio
from typing import Optional
import cv2
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.schemas.camera import (
    CameraDeleteResponse,
    CameraListResponse,
    CameraSourceCreate,
    CameraSourceResponse,
    CameraSourceUpdate,
    CameraTestRequest,
    CameraTestResponse,
)
from api.schemas.detection import DetectionResponse, DetectionResult, DetectionValidation
from api.services.camera_service import camera_service
from api.services.validation_service import ValidationService
from api.routes.detection import _run_pipeline, vehicle_svc, parking_svc, event_svc

router = APIRouter(prefix="/api/cameras", tags=["cameras"])


@router.get("", response_model=CameraListResponse)
async def list_cameras(
    is_active: Optional[bool] = Query(None, description="Filter status aktif"),
    db: AsyncSession = Depends(get_db),
):
    """List all camera sources."""
    cameras = await camera_service.get_all(db, is_active=is_active)
    return {"cameras": cameras, "total": len(cameras)}


@router.post("", response_model=CameraSourceResponse, status_code=201)
async def create_camera(
    body: CameraSourceCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new camera source (RTSP, m3u8, HTTP)."""
    camera = await camera_service.create(db, body.model_dump())
    return camera


@router.post("/test", response_model=CameraTestResponse)
async def test_camera_stream_url(body: CameraTestRequest):
    """Test a stream URL without saving (useful during camera configuration)."""
    result = await camera_service.test_connection(body.url, body.stream_type or "auto")
    return result


@router.get("/{camera_id}", response_model=CameraSourceResponse)
async def get_camera(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get camera source details by ID."""
    camera = await camera_service.get_by_id(db, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")
    return camera


@router.put("/{camera_id}", response_model=CameraSourceResponse)
async def update_camera(
    camera_id: int,
    body: CameraSourceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing camera source."""
    camera = await camera_service.update(
        db, camera_id, body.model_dump(exclude_unset=True)
    )
    if not camera:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")
    return camera


@router.delete("/{camera_id}", response_model=CameraDeleteResponse)
async def delete_camera(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a camera source."""
    success = await camera_service.delete(db, camera_id)
    if not success:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")
    return {"message": "Kamera berhasil dihapus", "id": camera_id}


@router.post("/{camera_id}/test", response_model=CameraTestResponse)
async def test_existing_camera(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Test connection for an existing camera source."""
    camera = await camera_service.get_by_id(db, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")
    result = await camera_service.test_connection(camera.url, camera.stream_type)
    return result


@router.get("/{camera_id}/snapshot")
async def get_camera_snapshot(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Capture a single JPEG snapshot from the camera stream."""
    camera = await camera_service.get_by_id(db, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")

    frame = await camera_service.capture_frame(camera.url)
    if frame is None:
        placeholder = camera_service.create_placeholder_image(
            "Snapshot Gagal", f"{camera.name} offline atau stream terputus"
        )
        return Response(content=placeholder, media_type="image/jpeg")

    _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return Response(content=jpeg.tobytes(), media_type="image/jpeg")


@router.get("/{camera_id}/stream")
async def get_camera_stream(
    camera_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Stream MJPEG video feed from the camera (compatible with all browsers)."""
    camera = await camera_service.get_by_id(db, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")

    return StreamingResponse(
        camera_service.generate_mjpeg_stream(camera.url),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.post("/{camera_id}/detect", response_model=DetectionResponse)
async def detect_from_camera(
    camera_id: int,
    validate: bool = Query(True, description="Validasi plat terhadap database"),
    db: AsyncSession = Depends(get_db),
):
    """Capture a frame from the live camera and run ALPR plate detection."""
    camera = await camera_service.get_by_id(db, camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail="Kamera tidak ditemukan")

    frame = await camera_service.capture_frame(camera.url)
    if frame is None:
        raise HTTPException(
            status_code=502,
            detail="Gagal mengambil frame dari sumber kamera (kamera offline atau tidak merespons)",
        )

    result = await asyncio.to_thread(_run_pipeline, frame)

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

    return DetectionResponse(detection=detection, validation=validation)
