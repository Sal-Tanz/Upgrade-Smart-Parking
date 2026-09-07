"""
Schedule routes — CRUD for vehicle schedules.

See: https://fastapi.tiangolo.com/tutorial/path-params/
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from api.database import get_db
from api.services.schedule_service import ScheduleService
from api.schemas.schedule import ScheduleCreate, ScheduleUpdate, ScheduleResponse, ScheduleListResponse

router = APIRouter(prefix="/api/schedules", tags=["schedules"])
schedule_svc = ScheduleService()


@router.get("", response_model=ScheduleListResponse)
async def list_schedules(
    vehicle_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List all schedules, optionally filtered by vehicle_id."""
    schedules = await schedule_svc.get_schedules(db, vehicle_id=vehicle_id)
    return {"schedules": schedules, "total": len(schedules)}


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single schedule by ID."""
    schedules = await schedule_svc.get_schedules(db)
    schedule = next((s for s in schedules if s.id == schedule_id), None)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.post("", response_model=ScheduleResponse, status_code=201)
async def create_schedule(
    body: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new schedule."""
    schedule = await schedule_svc.create_schedule(db, body.model_dump())
    return schedule


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int,
    body: ScheduleUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing schedule."""
    schedule = await schedule_svc.update_schedule(db, schedule_id, body.model_dump(exclude_unset=True))
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.delete("/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a schedule."""
    deleted = await schedule_svc.delete_schedule(db, schedule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return None