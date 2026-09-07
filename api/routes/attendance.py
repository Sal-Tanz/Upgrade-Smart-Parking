"""Attendance routes — GET/POST/PUT/DELETE for attendance records."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.services.attendance_service import AttendanceService

router = APIRouter(prefix="/api/attendance", tags=["attendance"])
attendance_svc = AttendanceService()


@router.get("")
async def list_attendance(start_date: str | None = Query(None, description="YYYY-MM-DD"), end_date: str | None = Query(None, description="YYYY-MM-DD"), vehicle_id: int | None = Query(None), db: AsyncSession = Depends(get_db)):
    records = await attendance_svc.get_records(db, start_date=start_date, end_date=end_date, vehicle_id=vehicle_id)
    return {"records": [r.to_dict() for r in records], "total": len(records)}


@router.get("/summary")
async def attendance_summary(start_date: str | None = Query(None), end_date: str | None = Query(None), db: AsyncSession = Depends(get_db)):
    records = await attendance_svc.get_records(db, start_date=start_date, end_date=end_date)
    total = len(records)
    on_time = sum(1 for r in records if r.arrival_status == "TEPAT_WAKTU")
    late = sum(1 for r in records if r.arrival_status == "TERLAMBAT")
    return {"total_arrivals": total, "total_on_time": on_time, "total_late": late, "on_time_rate": round(on_time / total * 100, 1) if total else 0}


@router.get("/{record_id}")
async def get_attendance(record_id: int, db: AsyncSession = Depends(get_db)):
    record = await attendance_svc.get_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    return record.to_dict()


@router.post("", status_code=201)
async def create_attendance(vehicle_id: int = Query(...), plate_number: str = Query(...), arrival_time: str | None = Query(None), db: AsyncSession = Depends(get_db)):
    parsed_time = datetime.fromisoformat(arrival_time) if arrival_time else datetime.now(timezone.utc)
    try:
        record = await attendance_svc.create_record(db, vehicle_id, plate_number, parsed_time)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return record.to_dict()


@router.put("/{record_id}")
async def update_attendance(record_id: int, departure_time: str | None = Query(None), departure_status: str = Query("TEPAT_WAKTU"), db: AsyncSession = Depends(get_db)):
    record = await attendance_svc.get_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    parsed_time = datetime.fromisoformat(departure_time) if departure_time else datetime.now(timezone.utc)
    try:
        updated = await attendance_svc.update_departure(db, record_id, parsed_time, departure_status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return updated.to_dict() if updated else {}


@router.delete("/{record_id}", status_code=204)
async def delete_attendance(record_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await attendance_svc.delete_record(db, record_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    return None
