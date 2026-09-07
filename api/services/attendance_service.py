"""Attendance tracking service — arrival/departure evaluation and CRUD."""
import calendar
from datetime import datetime, timezone, date, timedelta
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.attendance_log import AttendanceLog
from api.models.vehicle import Vehicle
from api.models.vehicle_schedule import VehicleSchedule
from api.config import settings


def _to_local_time(dt: datetime) -> datetime:
    """Convert UTC datetime to configured local timezone."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    tz_offsets = {
        "Asia/Jakarta": 7,
        "Asia/Makassar": 8,
        "Asia/Jayapura": 9,
        "UTC": 0,
    }
    offset_hours = tz_offsets.get(settings.TIMEZONE, 7)
    return dt.astimezone(timezone(timedelta(hours=offset_hours)))


def _as_utc(dt: datetime) -> datetime:
    """Normalize naive/aware datetimes to timezone-aware UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class AttendanceService:
    """Service for tracking vehicle attendance."""

    async def _get_record_for_date(
        self, db: AsyncSession, vehicle_id: int, local_date: date
    ) -> Optional[AttendanceLog]:
        stmt = select(AttendanceLog).where(
            and_(
                AttendanceLog.vehicle_id == vehicle_id,
                AttendanceLog.date == local_date.isoformat(),
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_schedule(
        self, db: AsyncSession, vehicle_id: int, day_of_week: int
    ) -> Optional[VehicleSchedule]:
        stmt = select(VehicleSchedule).where(
            and_(
                VehicleSchedule.vehicle_id == vehicle_id,
                VehicleSchedule.day_of_week == day_of_week,
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def process_detection(
        self,
        db: AsyncSession,
        vehicle_id: int,
        plate_text: str,
        detection_time: datetime,
    ) -> dict:
        """Process a vehicle detection and determine ARRIVAL or DEPARTURE."""
        vehicle = await db.get(Vehicle, vehicle_id)
        if not vehicle:
            raise ValueError("Vehicle not found")

        normalized_plate = plate_text.strip().upper()
        if not normalized_plate:
            raise ValueError("Plate number is required")
        if vehicle.plat.strip().upper() != normalized_plate:
            raise ValueError("Plate number does not match vehicle")
        if not vehicle.aktif:
            raise ValueError("Vehicle is inactive")

        local_time = _to_local_time(detection_time)
        today = local_time.date()
        schedule = await self._get_schedule(db, vehicle_id, local_time.weekday())
        existing = await self._get_record_for_date(db, vehicle_id, today)

        if existing and existing.arrival_time and not existing.departure_time:
            return await self._record_departure(db, existing, detection_time, schedule)

        if existing and existing.departure_time:
            return {
                "action": "IGNORED",
                "record": existing,
                "status": "SUDAH_PULANG",
            }

        arrival_eval = self._evaluate_arrival(detection_time, schedule)
        log = AttendanceLog(
            vehicle_id=vehicle_id,
            date=today.isoformat(),
            arrival_time=detection_time,
            arrival_status=arrival_eval["status"],
            minutes_late=arrival_eval.get("minutes_late"),
            created_at=datetime.now(timezone.utc),
        )
        db.add(log)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            existing = await self._get_record_for_date(db, vehicle_id, today)
            if existing and existing.arrival_time and not existing.departure_time:
                return await self._record_departure(db, existing, detection_time, schedule)
            raise
        await db.refresh(log)
        return {
            "action": "ARRIVAL",
            "record": log,
            **arrival_eval,
        }

    async def _record_departure(
        self,
        db: AsyncSession,
        record: AttendanceLog,
        departure_time: datetime,
        schedule: Optional[VehicleSchedule],
    ) -> dict:
        if record.arrival_time and _as_utc(departure_time) < _as_utc(record.arrival_time):
            raise ValueError("Departure time cannot be earlier than arrival time")

        departure_eval = self._evaluate_departure(departure_time, schedule)
        record.departure_time = departure_time
        record.departure_status = departure_eval["status"]
        if record.arrival_time:
            diff = _as_utc(departure_time) - _as_utc(record.arrival_time)
            record.parking_duration_minutes = int(diff.total_seconds() / 60)
        await db.commit()
        await db.refresh(record)
        return {
            "action": "DEPARTURE",
            "record": record,
            **departure_eval,
        }

    async def get_records(
        self,
        db: AsyncSession,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        vehicle_id: Optional[int] = None,
    ) -> list[AttendanceLog]:
        """Get attendance records with optional date and vehicle filters."""
        conditions = []
        if start_date:
            conditions.append(AttendanceLog.date >= start_date)
        if end_date:
            conditions.append(AttendanceLog.date <= end_date)
        if vehicle_id is not None:
            conditions.append(AttendanceLog.vehicle_id == vehicle_id)

        stmt = select(AttendanceLog)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(AttendanceLog.date.desc(), AttendanceLog.id.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, db: AsyncSession, record_id: int) -> Optional[AttendanceLog]:
        """Get one attendance record by primary key."""
        return await db.get(AttendanceLog, record_id)

    async def create_record(
        self,
        db: AsyncSession,
        vehicle_id: int,
        plate_number: str,
        arrival_time: datetime,
    ) -> AttendanceLog:
        """Create a manual arrival record after validating the vehicle identity."""
        vehicle = await db.get(Vehicle, vehicle_id)
        if not vehicle:
            raise ValueError("Vehicle not found")
        if vehicle.plat.strip().upper() != plate_number.strip().upper():
            raise ValueError("Plate number does not match vehicle")
        if not vehicle.aktif:
            raise ValueError("Vehicle is inactive")

        local_time = _to_local_time(arrival_time)
        existing = await self._get_record_for_date(db, vehicle_id, local_time.date())
        if existing:
            raise ValueError("Attendance record already exists for this vehicle and date")

        schedule = await self._get_schedule(db, vehicle_id, local_time.weekday())
        arrival_eval = self._evaluate_arrival(arrival_time, schedule)
        record = AttendanceLog(
            vehicle_id=vehicle_id,
            date=local_time.date().isoformat(),
            arrival_time=arrival_time,
            arrival_status=arrival_eval["status"],
            minutes_late=arrival_eval.get("minutes_late"),
            created_at=datetime.now(timezone.utc),
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    async def update_departure(
        self,
        db: AsyncSession,
        record_id: int,
        departure_time: datetime,
        departure_status: str,
    ) -> Optional[AttendanceLog]:
        """Set departure information and persist parking duration."""
        record = await self.get_by_id(db, record_id)
        if not record:
            return None
        if record.arrival_time and _as_utc(departure_time) < _as_utc(record.arrival_time):
            raise ValueError("Departure time cannot be earlier than arrival time")

        status_map = {
            "ON_TIME": "TEPAT_WAKTU",
            "TEPAT_WAKTU": "TEPAT_WAKTU",
            "PULANG_CEPAT": "PULANG_CEPAT",
            "PULANG_LEMBUR": "PULANG_LEMBUR",
            "TIDAK_ADA_JADWAL": "TIDAK_ADA_JADWAL",
        }
        normalized_status = status_map.get(departure_status)
        if normalized_status is None:
            raise ValueError(f"Invalid departure status: {departure_status}")

        record.departure_time = departure_time
        record.departure_status = normalized_status
        if record.arrival_time:
            diff = _as_utc(departure_time) - _as_utc(record.arrival_time)
            record.parking_duration_minutes = int(diff.total_seconds() / 60)
        await db.commit()
        await db.refresh(record)
        return record

    async def delete_record(self, db: AsyncSession, record_id: int) -> bool:
        """Delete an attendance record."""
        record = await self.get_by_id(db, record_id)
        if not record:
            return False
        await db.delete(record)
        await db.commit()
        return True

    def _evaluate_arrival(self, actual_time: datetime, schedule: Optional[VehicleSchedule]) -> dict:
        """Evaluate arrival punctuality."""
        if not schedule or not schedule.expected_arrival:
            return {"status": "TIDAK_ADA_JADWAL"}

        local_time = _to_local_time(actual_time)
        expected = schedule.expected_arrival
        tolerance = schedule.tolerance_minutes if schedule.tolerance_minutes is not None else 15

        actual_minutes = local_time.hour * 60 + local_time.minute
        expected_minutes = expected.hour * 60 + expected.minute
        diff = actual_minutes - expected_minutes

        if abs(diff) <= tolerance or diff < 0:
            return {"status": "TEPAT_WAKTU", "minutes_late": 0}
        return {"status": "TERLAMBAT", "minutes_late": diff}

    def _evaluate_departure(self, actual_time: datetime, schedule: Optional[VehicleSchedule]) -> dict:
        """Evaluate departure punctuality."""
        if not schedule or not schedule.expected_departure:
            return {"status": "TIDAK_ADA_JADWAL"}

        local_time = _to_local_time(actual_time)
        expected = schedule.expected_departure
        tolerance = schedule.tolerance_minutes if schedule.tolerance_minutes is not None else 15

        actual_minutes = local_time.hour * 60 + local_time.minute
        expected_minutes = expected.hour * 60 + expected.minute
        diff = actual_minutes - expected_minutes

        if abs(diff) <= tolerance:
            return {"status": "TEPAT_WAKTU"}
        if diff < 0:
            return {"status": "PULANG_CEPAT", "minutes_early": abs(diff)}
        return {"status": "PULANG_LEMBUR", "minutes_overtime": diff}

    async def get_today_attendance(self, db: AsyncSession) -> list[AttendanceLog]:
        """Get all attendance records for the current configured local date."""
        today = _to_local_time(datetime.now(timezone.utc)).date().isoformat()
        return await self.get_records(db, start_date=today, end_date=today)

    async def get_monthly_recap(self, db: AsyncSession, year: int, month: int) -> list[dict]:
        """Get monthly attendance recap."""
        days = calendar.monthrange(year, month)[1]
        start_date = date(year, month, 1).isoformat()
        end_date = date(year, month, days).isoformat()
        records = await self.get_records(db, start_date=start_date, end_date=end_date)

        by_vehicle: dict[int, list[AttendanceLog]] = {}
        for record in records:
            by_vehicle.setdefault(record.vehicle_id, []).append(record)

        return [
            {
                "vehicle_id": vehicle_id,
                "hadir": len([r for r in logs if r.arrival_time]),
                "tepat_waktu": len([r for r in logs if r.arrival_status == "TEPAT_WAKTU"]),
                "terlambat": len([r for r in logs if r.arrival_status == "TERLAMBAT"]),
                "pulang_cepat": len([r for r in logs if r.departure_status == "PULANG_CEPAT"]),
                "lembur": len([r for r in logs if r.departure_status == "PULANG_LEMBUR"]),
            }
            for vehicle_id, logs in by_vehicle.items()
        ]
