"""Attendance schemas."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, time

class AttendanceRecord(BaseModel):
    vehicle_id: int
    date: str  # YYYY-MM-DD
    arrival_time: Optional[datetime] = None
    departure_time: Optional[datetime] = None
    arrival_status: Optional[str] = None  # TEPAT_WAKTU, TERLAMBAT, TIDAK_ADA_JADWAL
    departure_status: Optional[str] = None  # TEPAT_WAKTU, PULANG_CEPAT, PULANG_LEMBUR, TIDAK_ADA_JADWAL
    minutes_late: Optional[int] = None
    minutes_early: Optional[int] = None
    minutes_overtime: Optional[int] = None
    parking_duration_minutes: Optional[int] = None

    class Config:
        from_attributes = True

class AttendanceListResponse(BaseModel):
    records: list[AttendanceRecord]
    total: int

class AttendanceSummary(BaseModel):
    total_days: int
    on_time_arrivals: int
    late_arrivals: int
    on_time_departures: int
    early_departures: int
    overtime: int
    punctuality_rate: float  # 0.0 to 1.0
