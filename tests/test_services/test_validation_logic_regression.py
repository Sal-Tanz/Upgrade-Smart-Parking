import pytest

from api.services.validation_service import ValidationService


class FakeVehicle:
    aktif = True
    jabatan = "S"


class FakeVehicleService:
    async def get_by_plate(self, db, plate):
        return FakeVehicle()


class FakeParkingService:
    def __init__(self, status):
        self.status = status

    def get_slot(self, slot_id):
        return {"cluster": "Orange", "status": self.status}


@pytest.mark.asyncio
async def test_occupied_slot_is_rejected():
    service = ValidationService(FakeVehicleService(), FakeParkingService("terisi"))

    result = await service.validate_parking(None, "D 1234 ABC", "O-01")

    assert result["is_valid"] is False
    assert result["violation_type"] == "OCCUPIED_SLOT"


@pytest.mark.asyncio
async def test_empty_slot_is_accepted_for_matching_cluster():
    service = ValidationService(FakeVehicleService(), FakeParkingService("kosong"))

    result = await service.validate_parking(None, "D 1234 ABC", "O-01")

    assert result["is_valid"] is True
    assert result["violation_type"] == "NONE"
