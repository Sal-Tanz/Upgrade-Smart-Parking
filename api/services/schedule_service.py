"""Vehicle schedule CRUD service."""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.models.vehicle_schedule import VehicleSchedule


class ScheduleService:
    """Service for managing vehicle schedules."""

    async def get_schedules(
        self, db: AsyncSession, vehicle_id: Optional[int] = None
    ) -> list[VehicleSchedule]:
        """Get schedules, optionally filtered by vehicle_id."""
        stmt = select(VehicleSchedule)
        if vehicle_id:
            stmt = stmt.where(VehicleSchedule.vehicle_id == vehicle_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create_schedule(self, db: AsyncSession, data: dict) -> VehicleSchedule:
        """Create a new schedule entry."""
        schedule = VehicleSchedule(**data)
        db.add(schedule)
        await db.commit()
        await db.refresh(schedule)
        return schedule

    async def update_schedule(
        self, db: AsyncSession, schedule_id: int, data: dict
    ) -> Optional[VehicleSchedule]:
        """Update an existing schedule."""
        stmt = select(VehicleSchedule).where(VehicleSchedule.id == schedule_id)
        result = await db.execute(stmt)
        schedule = result.scalar_one_or_none()
        if not schedule:
            return None
        for key, value in data.items():
            if hasattr(schedule, key) and value is not None:
                setattr(schedule, key, value)
        await db.commit()
        await db.refresh(schedule)
        return schedule

    async def delete_schedule(self, db: AsyncSession, schedule_id: int) -> bool:
        """Delete a schedule."""
        stmt = select(VehicleSchedule).where(VehicleSchedule.id == schedule_id)
        result = await db.execute(stmt)
        schedule = result.scalar_one_or_none()
        if not schedule:
            return False
        await db.delete(schedule)
        await db.commit()
        return True