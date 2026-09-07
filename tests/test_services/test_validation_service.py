"""Tests for ValidationService."""
import pytest
import json
import tempfile
import os
from api.services.vehicle_service import VehicleService
from api.services.parking_service import ParkingService
from api.services.validation_service import ValidationService


@pytest.fixture
def slot_config():
    """Sample slot config for testing."""
    config = {
        "slots": [
            {"slot_id": "M-01", "cluster": "Merah"},
            {"slot_id": "M-02", "cluster": "Merah"},
            {"slot_id": "O-01", "cluster": "Orange"},
            {"slot_id": "O-02", "cluster": "Orange"},
        ]
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        path = f.name
    yield path
    os.unlink(path)


@pytest.mark.asyncio
async def test_validate_plate_registered_dekan(db, slot_config):
    svc = ValidationService(VehicleService(), ParkingService(slot_config))
    await svc.vehicle_svc.create(db, {"plat": "B1234XY", "jabatan": "D"})
    result = await svc.validate_plate(db, "B1234XY")
    assert result["is_registered"] is True
    assert result["status"] == "ACCEPTED"
    assert result["jabatan"] == "D"
    assert result["cluster"] == "Merah"


@pytest.mark.asyncio
async def test_validate_plate_registered_dosen(db, slot_config):
    svc = ValidationService(VehicleService(), ParkingService(slot_config))
    await svc.vehicle_svc.create(db, {"plat": "D5678ZZ", "jabatan": "S"})
    result = await svc.validate_plate(db, "D5678ZZ")
    assert result["is_registered"] is True
    assert result["cluster"] == "Orange"


@pytest.mark.asyncio
async def test_validate_plate_not_registered(db, slot_config):
    svc = ValidationService(VehicleService(), ParkingService(slot_config))
    result = await svc.validate_plate(db, "NOTFOUND")
    assert result["is_registered"] is False
    assert result["status"] == "REJECTED"
    assert result["buzzer_pattern"] == "LONG_3X"


@pytest.mark.asyncio
async def test_validate_plate_case_insensitive(db, slot_config):
    svc = ValidationService(VehicleService(), ParkingService(slot_config))
    await svc.vehicle_svc.create(db, {"plat": "B1234XY", "jabatan": "D"})
    result = await svc.validate_plate(db, "b1234xy")
    assert result["is_registered"] is True


@pytest.mark.asyncio
async def test_validate_parking_dekan_in_merah(db, slot_config):
    svc = ValidationService(VehicleService(), ParkingService(slot_config))
    await svc.vehicle_svc.create(db, {"plat": "BAAAAA", "jabatan": "D"})
    svc.parking_svc.update_status("M-01", "kosong")
    result = await svc.validate_parking(db, "BAAAAA", "M-01")
    assert result["is_valid"] is True
    assert result["buzzer_pattern"] == "SUCCESS_TONE"


@pytest.mark.asyncio
async def test_validate_parking_dosen_in_merah_should_fail(db, slot_config):
    svc = ValidationService(VehicleService(), ParkingService(slot_config))
    await svc.vehicle_svc.create(db, {"plat": "S1234CC", "jabatan": "S"})
    svc.parking_svc.update_status("M-01", "kosong")
    result = await svc.validate_parking(db, "S1234CC", "M-01")
    assert result["is_valid"] is False
    assert result["violation_type"] == "WRONG_CLUSTER"
    assert result["buzzer_pattern"] == "MEDIUM_2X"


@pytest.mark.asyncio
async def test_validate_parking_dekan_in_orange_is_allowed(db, slot_config):
    svc = ValidationService(VehicleService(), ParkingService(slot_config))
    await svc.vehicle_svc.create(db, {"plat": "B1111A", "jabatan": "D"})
    svc.parking_svc.update_status("O-01", "kosong")
    result = await svc.validate_parking(db, "B1111A", "O-01")
    # Dekan boleh fallback ke Orange
    assert result["is_valid"] is True
    assert result["buzzer_pattern"] == "SUCCESS_TONE"


@pytest.mark.asyncio
async def test_validate_parking_unregistered(db, slot_config):
    svc = ValidationService(VehicleService(), ParkingService(slot_config))
    result = await svc.validate_parking(db, "NOTFOUND", "M-01")
    assert result["is_valid"] is False
    assert result["violation_type"] == "UNREGISTERED"


@pytest.mark.asyncio
async def test_validate_parking_invalid_slot(db, slot_config):
    svc = ValidationService(VehicleService(), ParkingService(slot_config))
    await svc.vehicle_svc.create(db, {"plat": "B2222B", "jabatan": "D"})
    result = await svc.validate_parking(db, "B2222B", "INVALID")
    assert result["is_valid"] is False
    assert result["violation_type"] == "INVALID_SLOT"