"""Event logging and querying service."""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from api.models.parking_event import ParkingEvent
from api.event_bus import event_bus


class EventService:
    """Service for logging and querying parking events."""

    async def log_event(
        self,
        db: AsyncSession,
        plate_number: str,
        event_type: str,
        slot_id: Optional[str] = None,
        cluster: Optional[str] = None,
        jabatan: Optional[str] = None,
        validation_result: Optional[str] = None,
        confidence_score: Optional[float] = None,
        buzzer_pattern: Optional[str] = None,
    ) -> ParkingEvent:
        """Log a parking event and broadcast via event bus."""
        event = ParkingEvent(
            plate_number=plate_number,
            event_type=event_type,
            slot_id=slot_id,
            cluster=cluster,
            jabatan=jabatan,
            validation_result=validation_result,
            confidence_score=confidence_score,
            buzzer_pattern=buzzer_pattern,
            created_at=datetime.now(timezone.utc),
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

        # Broadcast ke WebSocket subscribers
        await event_bus.publish({
            "id": event.id,
            "type": event.event_type,
            "plate": event.plate_number,
            "slot_id": event.slot_id,
            "cluster": event.cluster,
            "timestamp": event.created_at.isoformat(),
            "buzzer": event.buzzer_pattern,
        })

        return event

    async def get_events(
        self,
        db: AsyncSession,
        event_type: Optional[str] = None,
        plate_number: Optional[str] = None,
        resolved: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ParkingEvent], int]:
        """Get paginated events with optional filters."""
        conditions = []
        if event_type:
            conditions.append(ParkingEvent.event_type == event_type)
        if plate_number:
            conditions.append(ParkingEvent.plate_number == plate_number)
        if resolved is not None:
            conditions.append(ParkingEvent.resolved == resolved)

        # Count
        count_stmt = select(func.count()).select_from(ParkingEvent)
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        total = (await db.execute(count_stmt)).scalar() or 0

        # Query
        stmt = select(ParkingEvent).order_by(ParkingEvent.created_at.desc())
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.limit(limit).offset(offset)
        result = await db.execute(stmt)
        events = list(result.scalars().all())

        return events, total

    async def resolve_event(self, db: AsyncSession, event_id: int) -> Optional[ParkingEvent]:
        """Mark an event as resolved."""
        stmt = select(ParkingEvent).where(ParkingEvent.id == event_id)
        result = await db.execute(stmt)
        event = result.scalar_one_or_none()
        if event:
            event.resolved = True
            await db.commit()
            await db.refresh(event)
        return event

    async def get_unresolved_count(self, db: AsyncSession) -> int:
        """Get count of unresolved events."""
        stmt = select(func.count()).select_from(ParkingEvent).where(
            ParkingEvent.resolved.is_(False)
        )
        result = await db.execute(stmt)
        return result.scalar() or 0