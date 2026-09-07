"""Event endpoints including WebSocket."""
import json
from fastapi import APIRouter, Depends, Query, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from api.database import get_db
from api.services.event_service import EventService
from api.models.parking_event import ParkingEvent
from api.event_bus import event_bus
from api.schemas.event import EventListResponse, EventResponse

router = APIRouter(prefix="/api/events", tags=["events"])
event_svc = EventService()


@router.get("", response_model=EventListResponse)
async def list_events(
    event_type: str | None = Query(None),
    plate_number: str | None = Query(None),
    resolved: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated event log."""
    events, total = await event_svc.get_events(
        db, event_type=event_type, plate_number=plate_number,
        resolved=resolved, limit=limit, offset=offset,
    )
    unresolved = await event_svc.get_unresolved_count(db)
    return {
        "events": events,
        "total": total,
        "unresolved_count": unresolved,
    }


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single event."""
    stmt = select(ParkingEvent).where(ParkingEvent.id == event_id)
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.post("/{event_id}/resolve")
async def resolve_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Mark an event as resolved."""
    event = await event_svc.resolve_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"ok": True, "id": event_id}


@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """WebSocket endpoint for real-time event streaming."""
    await websocket.accept()
    queue = event_bus.subscribe()
    try:
        while True:
            event = await queue.get()
            try:
                await websocket.send_text(json.dumps(event, default=str))
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    finally:
        event_bus.unsubscribe(queue)