"""Attendance log ORM model."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from api.models.base import Base


class AttendanceLog(Base):
    __tablename__ = "attendance_log"
    __table_args__ = (
        UniqueConstraint("vehicle_id", "date", name="uq_attendance_vehicle_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    vehicle_id = Column(Integer, ForeignKey("kendaraan.id"), nullable=False)
    date = Column(String(10), nullable=False)  # YYYY-MM-DD in configured local timezone
    arrival_time = Column(DateTime)
    departure_time = Column(DateTime)
    arrival_status = Column(String(20))  # TEPAT_WAKTU, TERLAMBAT, TIDAK_ADA_JADWAL
    departure_status = Column(String(20))  # TEPAT_WAKTU, PULANG_CEPAT, PULANG_LEMBUR, TIDAK_ADA_JADWAL
    minutes_late = Column(Integer)
    minutes_early = Column(Integer)
    minutes_overtime = Column(Integer)
    parking_duration_minutes = Column(Integer)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self) -> dict:
        """Serialize the ORM record for API responses."""
        return {
            "id": self.id,
            "vehicle_id": self.vehicle_id,
            "date": self.date,
            "arrival_time": self.arrival_time,
            "departure_time": self.departure_time,
            "arrival_status": self.arrival_status,
            "departure_status": self.departure_status,
            "minutes_late": self.minutes_late,
            "minutes_early": self.minutes_early,
            "minutes_overtime": self.minutes_overtime,
            "parking_duration_minutes": self.parking_duration_minutes,
        }
