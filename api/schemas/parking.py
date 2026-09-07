"""Parking-related schemas."""
from pydantic import BaseModel, Field
from typing import Optional

class SlotStatus(BaseModel):
    slot_id: str
    cluster: str
    status: str  # available, occupied, reserved
    vehicle_plat: Optional[str] = None

class ParkingValidationRequest(BaseModel):
    plate_number: str = Field(..., max_length=20)
    slot_id: str = Field(..., max_length=20)

class ParkingValidationResponse(BaseModel):
    is_valid: bool
    slot_id: str
    expected_cluster: Optional[str] = None
    actual_cluster: Optional[str] = None
    violation_type: Optional[str] = None
    message: str
    buzzer_pattern: str  # NONE, SHORT, MEDIUM, LONG, DOUBLE

class SlotListResponse(BaseModel):
    slots: list[SlotStatus]
    total: int
    available_count: int
