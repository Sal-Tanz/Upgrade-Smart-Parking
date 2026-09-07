"""Parking event log ORM model."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float
from api.models.base import Base

class ParkingEvent(Base):
    __tablename__ = "parking_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plate_number = Column(String(20), nullable=False)
    event_type = Column(String(50), nullable=False)  # entry, exit, violation
    slot_id = Column(String(20))
    cluster = Column(String(50))
    jabatan = Column(String(10))
    validation_result = Column(String(50))
    confidence_score = Column(Float)
    buzzer_pattern = Column(String(20))
    resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
