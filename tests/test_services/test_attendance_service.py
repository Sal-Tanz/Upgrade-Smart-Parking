"""Regression tests for attendance service/API consistency."""
from datetime import datetime, timezone

import pytest

from api.models.attendance_log import AttendanceLog
from api.services.attendance_service import AttendanceService, _to_local_time


def test_attendance_service_exposes_route_methods():
    """All methods used by attendance routes must exist on the service."""
    required = {"get_records", "get_by_id", "create_record", "update_departure", "delete_record"}
    missing = [name for name in required if not hasattr(AttendanceService, name)]
    assert not missing, f"AttendanceService missing route methods: {missing}"


def test_attendance_log_has_unique_vehicle_date_constraint():
    """A vehicle can have at most one attendance record per local date."""
    constraints = AttendanceLog.__table__.constraints
    assert any(
        constraint.__class__.__name__ == "UniqueConstraint"
        and {column.name for column in constraint.columns} == {"vehicle_id", "date"}
        for constraint in constraints
    )


def test_attendance_log_has_parking_duration_column():
    """Parking duration must be persisted instead of being a transient attribute."""
    assert "parking_duration_minutes" in AttendanceLog.__table__.columns


def test_process_detection_uses_local_date_for_reporting(monkeypatch):
    """Records around UTC midnight must use the configured local calendar date."""
    from api.services import attendance_service
    monkeypatch.setattr(attendance_service.settings, "TIMEZONE", "Asia/Jakarta")

    # 2026-08-24 23:30 UTC == 2026-08-25 06:30 WIB.
    local = _to_local_time(datetime(2026, 8, 24, 23, 30, tzinfo=timezone.utc))
    assert local.date().isoformat() == "2026-08-25"
