"""Camera source ORM model."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from api.models.base import Base

class CameraSource(Base):
    __tablename__ = "camera_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    url = Column(String(1000), nullable=False)
    stream_type = Column(String(50), default="auto", nullable=False)
    location = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    @property
    def resolved_stream_type(self) -> str:
        if self.stream_type and self.stream_type.lower() not in ("auto", ""):
            st = self.stream_type.lower()
            return "rtsp" if st == "rstp" else st
        url_lower = (self.url or "").lower().strip()
        if url_lower.startswith(("rtsp://", "rtsps://", "rstp://", "rstps://")):
            return "rtsp"
        if ".m3u8" in url_lower:
            return "m3u8"
        if url_lower.isdigit() or url_lower.startswith("/dev/video"):
            return "device"
        return "http"

