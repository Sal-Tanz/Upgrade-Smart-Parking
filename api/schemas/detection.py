"""Detection schemas."""
from pydantic import BaseModel, Field
from typing import Optional


class DetectionResult(BaseModel):
    plate_text: str
    raw_plate_text: str
    detection_confidence: float
    ocr_confidence: float
    overall_confidence: float
    bbox: Optional[list[int]] = None
    vehicle_status: str
    is_valid_format: bool
    ocr_engine_used: str
    error_message: Optional[str] = None


class DetectionValidation(BaseModel):
    is_registered: bool
    status: str
    plate_text: str
    jabatan: Optional[str] = None
    cluster: Optional[str] = None
    reason: str
    buzzer_pattern: Optional[str] = None


class DetectionResponse(BaseModel):
    detection: DetectionResult
    validation: Optional[DetectionValidation] = None


class DetectionListResponse(BaseModel):
    results: list[DetectionResponse]
    total: int
