"""Plate annotation ORM model for training dataset."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime
from api.models.base import Base

class PlateAnnotation(Base):
    __tablename__ = "plate_annotations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_path = Column(String(255), nullable=False)
    plate_text = Column(String(20), nullable=False)
    bbox_x1 = Column(Float)
    bbox_y1 = Column(Float)
    bbox_x2 = Column(Float)
    bbox_y2 = Column(Float)
    confidence = Column(Float)
    annotated_by = Column(String(100))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
