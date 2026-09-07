"""Tests for VehicleService."""
import pytest
from api.services.vehicle_service import VehicleService

@pytest.mark.asyncio
async def test_create_vehicle(db):
    svc = VehicleService()
    vehicle = await svc.create(db, {"plat": "B1234CD", "jabatan": "D"})
    assert vehicle.id is not None
    assert vehicle.plat == "B1234CD"
    assert vehicle.jabatan == "D"
    assert vehicle.cluster_hak == "Merah"

@pytest.mark.asyncio
async def test_create_vehicle_staff(db):
    svc = VehicleService()
    vehicle = await svc.create(db, {"plat": "B5678EF", "jabatan": "S"})
    assert vehicle.cluster_hak == "Orange"

@pytest.mark.asyncio
async def test_get_by_plate(db):
    svc = VehicleService()
    await svc.create(db, {"plat": "B1111AA", "jabatan": "D"})
    vehicle = await svc.get_by_plate(db, "B1111AA")
    assert vehicle is not None
    assert vehicle.plat == "B1111AA"

@pytest.mark.asyncio
async def test_get_by_plate_not_found(db):
    svc = VehicleService()
    assert await svc.get_by_plate(db, "NOTFOUND") is None

@pytest.mark.asyncio
async def test_get_all(db):
    svc = VehicleService()
    await svc.create(db, {"plat": "B1000AA", "jabatan": "D"})
    await svc.create(db, {"plat": "B2000BB", "jabatan": "S"})
    vehicles = await svc.get_all(db)
    assert len(vehicles) >= 2

@pytest.mark.asyncio
async def test_get_all_with_filter(db):
    svc = VehicleService()
    await svc.create(db, {"plat": "B3000CC", "jabatan": "D"})
    await svc.create(db, {"plat": "B4000DD", "jabatan": "S"})
    vehicles = await svc.get_all(db, {"jabatan": "D"})
    assert all(v.jabatan == "D" for v in vehicles)

@pytest.mark.asyncio
async def test_update_vehicle(db):
    svc = VehicleService()
    vehicle = await svc.create(db, {"plat": "B5000EE", "jabatan": "D"})
    updated = await svc.update(db, "B5000EE", {"jabatan": "W"})
    assert updated.jabatan == "W"
    assert updated.cluster_hak == "Merah"

@pytest.mark.asyncio
async def test_update_vehicle_recomputes_cluster(db):
    svc = VehicleService()
    await svc.create(db, {"plat": "B5001EE", "jabatan": "D"})
    updated = await svc.update(db, "B5001EE", {"jabatan": "S"})
    assert updated.jabatan == "S"
    assert updated.cluster_hak == "Orange"

@pytest.mark.asyncio
async def test_update_not_found(db):
    svc = VehicleService()
    assert await svc.update(db, "NOTFOUND", {"jabatan": "W"}) is None

@pytest.mark.asyncio
async def test_deactivate_vehicle(db):
    svc = VehicleService()
    await svc.create(db, {"plat": "B6000FF", "jabatan": "D"})
    deactivated = await svc.deactivate(db, "B6000FF")
    assert deactivated.aktif is False

@pytest.mark.asyncio
async def test_deactivate_not_found(db):
    svc = VehicleService()
    assert await svc.deactivate(db, "NOTFOUND") is None
