"""Parking endpoints."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from api.database import get_db
from api.services.vehicle_service import VehicleService
from api.services.parking_service import ParkingService
from api.services.validation_service import ValidationService
from api.services.event_service import EventService
from api.config import settings

router = APIRouter(prefix="/api", tags=["parking"])
# Services instantiated at module level
vehicle_svc = VehicleService()
parking_svc = ParkingService(settings.SLOT_CONFIG_PATH)
validation_svc = ValidationService(vehicle_svc, parking_svc)
event_svc = EventService()


@router.get("/slots")
async def list_slots():
    """Get all parking slot statuses."""
    slots = parking_svc.get_all_slots()
    return {
        "slots": [
            {"slot_id": sid, "cluster": s["cluster"], "status": s["status"]}
            for sid, s in slots.items()
        ],
        "total": len(slots),
    }


@router.get("/slots/{slot_id}")
async def get_slot(slot_id: str):
    """Get a specific slot."""
    slot = parking_svc.get_slot(slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    return {"slot_id": slot_id, "cluster": slot["cluster"], "status": slot["status"]}


@router.post("/validate-plate")
async def validate_plate(
    plate_text: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Validate a plate number."""
    result = await validation_svc.validate_plate(db, plate_text)
    if result["status"] == "REJECTED":
        await event_svc.log_event(
            db, plate_number=plate_text, event_type="REJECTED",
            validation_result=result["status"], buzzer_pattern=result.get("buzzer_pattern"),
        )
    return result


@router.post("/validate-parking")
async def validate_parking(
    plate_text: str = Query(...),
    slot_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Validate parking position."""
    result = await validation_svc.validate_parking(db, plate_text, slot_id)
    event_type = "VALID" if result["is_valid"] else "VIOLATION"
    await event_svc.log_event(
        db,
        plate_number=plate_text,
        event_type=event_type,
        slot_id=slot_id,
        cluster=result.get("actual_cluster"),
        validation_result=result.get("violation_type"),
        buzzer_pattern=result.get("buzzer_pattern"),
    )
    return result