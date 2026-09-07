"""Vehicle endpoints."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from api.database import get_db
from api.services.vehicle_service import VehicleService
from api.schemas.vehicle import VehicleCreate, VehicleUpdate, VehicleResponse, VehicleListResponse, VehicleDeleteResponse, VehicleDeleteResponse

router = APIRouter(prefix="/api/vehicles", tags=["vehicles"])
vehicle_svc = VehicleService()


@router.get("", response_model=VehicleListResponse)
async def list_vehicles(
    jabatan: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    filters = {}
    if jabatan:
        filters["jabatan"] = jabatan
    vehicles = await vehicle_svc.get_all(db, filters)
    return {"vehicles": vehicles, "total": len(vehicles)}


@router.post("", response_model=VehicleResponse, status_code=201)
async def create_vehicle(
    body: VehicleCreate,
    db: AsyncSession = Depends(get_db),
):
    vehicle = await vehicle_svc.create(db, body.model_dump())
    return vehicle


@router.get("/{plate}", response_model=VehicleResponse)
async def get_vehicle(
    plate: str,
    db: AsyncSession = Depends(get_db),
):
    vehicle = await vehicle_svc.get_by_plate(db, plate)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Not found")
    return vehicle


@router.put("/{plate}", response_model=VehicleResponse)
async def update_vehicle(
    plate: str,
    body: VehicleUpdate,
    db: AsyncSession = Depends(get_db),
):
    vehicle = await vehicle_svc.update(db, plate, body.model_dump(exclude_unset=True))
    if not vehicle:
        raise HTTPException(status_code=404, detail="Not found")
    return vehicle


@router.delete("/{plate}", response_model=VehicleDeleteResponse)
async def delete_vehicle(
    plate: str,
    db: AsyncSession = Depends(get_db),
):
    vehicle = await vehicle_svc.deactivate(db, plate)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Not found")
    return VehicleDeleteResponse(ok=True, message=f"Vehicle {plate} deactivated")