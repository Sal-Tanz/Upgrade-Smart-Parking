"""Event schemas."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class EventBase(BaseModel):
    plate_number: str
    event_type: str  # entry, exit, violation
    slot_id: Optional[str] = None
    cluster: Optional[str] = None

class EventCreate(EventBase):
    jabatan: Optional[str] = None
    validation_result: Optional[str] = None
    confidence_score: Optional[float] = None
    buzzer_pattern: Optional[str] = None

class EventResponse(EventBase):
    id: int
    jabatan: Optional[str] = None
    validation_result: Optional[str] = None
    confidence_score: Optional[float] = None
    buzzer_pattern: Optional[str] = None
    resolved: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

class EventListResponse(BaseModel):
    events: list[EventResponse]
    total: int
    unresolved_count: int

class EventResolveRequest(BaseModel):
    resolved: bool = True
