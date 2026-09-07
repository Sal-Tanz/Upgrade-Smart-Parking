"""Schedule schemas."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import time

class ScheduleBase(BaseModel):
    vehicle_id: int
    day_of_week: int = Field(..., ge=0, le=6, description="0=Monday, 6=Sunday")
    expected_arrival: time
    expected_departure: time
    tolerance_minutes: int = 15

class ScheduleCreate(ScheduleBase):
    pass

class ScheduleUpdate(BaseModel):
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    expected_arrival: Optional[time] = None
    expected_departure: Optional[time] = None
    tolerance_minutes: Optional[int] = None

class ScheduleResponse(ScheduleBase):
    id: int

    class Config:
        from_attributes = True

class ScheduleListResponse(BaseModel):
    schedules: list[ScheduleResponse]
    total: int
