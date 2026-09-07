"""Vehicle CRUD service."""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.vehicle import Vehicle
from logic.karnaugh import compute_cluster


class VehicleService:
    """Service for vehicle CRUD operations."""

    async def get_by_plate(self, db: AsyncSession, plate: str) -> Optional[Vehicle]:
        stmt = select(Vehicle).where(Vehicle.plat == plate)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, db: AsyncSession, filters: Optional[dict] = None) -> list[Vehicle]:
        stmt = select(Vehicle)
        if filters:
            if "jabatan" in filters:
                stmt = stmt.where(Vehicle.jabatan == filters["jabatan"])
            if "aktif" in filters:
                stmt = stmt.where(Vehicle.aktif == filters["aktif"])
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, data: dict) -> Vehicle:
        """Create a vehicle using the Karnaugh logic as the single source of truth."""
        data = dict(data)
        jabatan = data.get("jabatan", "S")
        cluster = compute_cluster(jabatan)
        if cluster is None:
            raise ValueError(f"Invalid parking entitlement for jabatan: {jabatan!r}")
        data["cluster_hak"] = cluster

        vehicle = Vehicle(**data)
        db.add(vehicle)
        await db.flush()
        await db.refresh(vehicle)
        return vehicle

    async def update(self, db: AsyncSession, plate: str, data: dict) -> Optional[Vehicle]:
        """Update a vehicle and recompute cluster entitlement when jabatan changes."""
        vehicle = await self.get_by_plate(db, plate)
        if not vehicle:
            return None

        for key, value in data.items():
            if value is not None and hasattr(vehicle, key) and key != "cluster_hak":
                setattr(vehicle, key, value)

        if "jabatan" in data and data["jabatan"] is not None:
            cluster = compute_cluster(data["jabatan"])
            if cluster is None:
                raise ValueError(f"Invalid parking entitlement for jabatan: {data['jabatan']!r}")
            vehicle.cluster_hak = cluster

        await db.flush()
        await db.refresh(vehicle)
        return vehicle

    async def deactivate(self, db: AsyncSession, plate: str) -> Optional[Vehicle]:
        vehicle = await self.get_by_plate(db, plate)
        if not vehicle:
            return None
        vehicle.aktif = False
        await db.flush()
        await db.refresh(vehicle)
        return vehicle
