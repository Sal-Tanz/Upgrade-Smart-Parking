"""Attendance log ORM model."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
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

    vehicle = relationship("Vehicle", lazy="selectin")

    def to_dict(self) -> dict:
        """Serialize the ORM record for API responses."""
        plate = self.vehicle.plat if hasattr(self, "vehicle") and self.vehicle else None
        arr_iso = self.arrival_time.isoformat() if hasattr(self.arrival_time, "isoformat") else self.arrival_time
        dep_iso = self.departure_time.isoformat() if hasattr(self.departure_time, "isoformat") else self.departure_time
        return {
            "id": self.id,
            "vehicle_id": self.vehicle_id,
            "plate_number": plate or f"Vehicle #{self.vehicle_id}",
            "date": self.date,
            "arrival_time": arr_iso,
            "departure_time": dep_iso,
            "entry_time": arr_iso,
            "exit_time": dep_iso,
            "arrival_status": self.arrival_status,
            "departure_status": self.departure_status,
            "minutes_late": self.minutes_late,
            "minutes_early": self.minutes_early,
            "minutes_overtime": self.minutes_overtime,
            "duration_minutes": self.parking_duration_minutes,
            "parking_duration_minutes": self.parking_duration_minutes,
            "status": "completed" if self.departure_time else "active",
        }

