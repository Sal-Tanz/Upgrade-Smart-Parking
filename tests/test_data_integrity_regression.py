"""Regression tests for attendance data integrity."""
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from api.models.vehicle import Vehicle
from api.models.vehicle_schedule import VehicleSchedule
from api.services.attendance_service import AttendanceService


@pytest.mark.asyncio
async def test_process_detection_rejects_plate_mismatch(db):
    """A detection must not create attendance for a different registered plate."""
    vehicle = Vehicle(
        plat="B 1234 ABC",
        nama_pemilik="Test Owner",
        jabatan="S",
        cluster_hak="Orange",
        aktif=True,
    )
    db.add(vehicle)
    await db.commit()
    await db.refresh(vehicle)

    service = AttendanceService()
    with pytest.raises(ValueError, match="Plate number does not match vehicle"):
        await service.process_detection(
            db=db,
            vehicle_id=vehicle.id,
            plate_text="B 9999 XYZ",
            detection_time=datetime(2026, 8, 25, 8, 0, tzinfo=timezone.utc),
        )


@pytest.mark.asyncio
async def test_vehicle_schedule_is_unique_per_weekday(db):
    """A vehicle cannot have two schedules for the same weekday."""
    vehicle = Vehicle(
        plat="B 5678 DEF",
        nama_pemilik="Test Owner",
        jabatan="S",
        cluster_hak="Orange",
        aktif=True,
    )
    db.add(vehicle)
    await db.commit()
    await db.refresh(vehicle)

    db.add(VehicleSchedule(vehicle_id=vehicle.id, day_of_week=0))
    await db.commit()

    db.add(VehicleSchedule(vehicle_id=vehicle.id, day_of_week=0))
    with pytest.raises(IntegrityError):
        await db.commit()
