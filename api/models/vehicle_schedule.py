"""Vehicle schedule ORM model for attendance tracking."""
from sqlalchemy import Column, Integer, Time, ForeignKey, UniqueConstraint
from api.models.base import Base


class VehicleSchedule(Base):
    __tablename__ = "vehicle_schedules"
    __table_args__ = (
        UniqueConstraint(
            "vehicle_id", "day_of_week", name="uq_vehicle_schedule_vehicle_day"
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    vehicle_id = Column(Integer, ForeignKey("kendaraan.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    expected_arrival = Column(Time)
    expected_departure = Column(Time)
    tolerance_minutes = Column(Integer, default=15)
