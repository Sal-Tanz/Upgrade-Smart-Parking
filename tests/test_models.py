"""Tests for Vehicle model."""
import pytest
from sqlalchemy import select
from api.models.vehicle import Vehicle

@pytest.mark.asyncio
async def test_create_vehicle(db):
    """Test creating a vehicle record."""
    vehicle = Vehicle(
        plat="B 1234 ABC",
        nama_pemilik="John Doe",
        jabatan="D",
        cluster_hak="Merah",
        aktif=True
    )
    db.add(vehicle)
    await db.commit()
    await db.refresh(vehicle)

    assert vehicle.id is not None
    assert vehicle.plat == "B 1234 ABC"
    assert vehicle.nama_pemilik == "John Doe"
    assert vehicle.jabatan == "D"
    assert vehicle.cluster_hak == "Merah"
    assert vehicle.aktif is True
    assert vehicle.created_at is not None

@pytest.mark.asyncio
async def test_vehicle_unique_plat(db):
    """Test that plat must be unique."""
    vehicle1 = Vehicle(plat="B 1234 ABC", jabatan="D", cluster_hak="Merah")
    vehicle2 = Vehicle(plat="B 1234 ABC", jabatan="W", cluster_hak="Orange")

    db.add(vehicle1)
    await db.commit()

    db.add(vehicle2)
    with pytest.raises(Exception):  # IntegrityError
        await db.commit()

@pytest.mark.asyncio
async def test_query_vehicles(db):
    """Test querying vehicles."""
    # Add test data
    vehicles = [
        Vehicle(plat="B 1111 AAA", jabatan="D", cluster_hak="Merah"),
        Vehicle(plat="B 2222 BBB", jabatan="W", cluster_hak="Orange"),
        Vehicle(plat="B 3333 CCC", jabatan="S", cluster_hak="Orange"),
    ]
    db.add_all(vehicles)
    await db.commit()

    # Query all
    result = await db.execute(select(Vehicle))
    all_vehicles = result.scalars().all()
    assert len(all_vehicles) == 3

    # Query by jabatan
    result = await db.execute(select(Vehicle).where(Vehicle.jabatan == "D"))
    dekan_vehicles = result.scalars().all()
    assert len(dekan_vehicles) == 1
    assert dekan_vehicles[0].plat == "B 1111 AAA"
