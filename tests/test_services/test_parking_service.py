"""Tests for ParkingService."""
import pytest
import json
import tempfile
import os

@pytest.fixture
def sample_config():
    """Create a temporary config file."""
    config = {
        "slots": [
            {"slot_id": "M-01", "cluster": "Merah", "polygon": [[0,0],[1,0],[1,1],[0,1]], "center": [0.5, 0.5]},
            {"slot_id": "M-02", "cluster": "Merah", "polygon": [[1,0],[2,0],[2,1],[1,1]], "center": [1.5, 0.5]},
            {"slot_id": "O-01", "cluster": "Orange", "polygon": [[0,1],[1,1],[1,2],[0,2]], "center": [0.5, 1.5]},
            {"slot_id": "O-02", "cluster": "Orange", "polygon": [[1,1],[2,1],[2,2],[1,2]], "center": [1.5, 1.5]},
        ]
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        path = f.name
    yield path
    os.unlink(path)

def test_load_config(sample_config):
    from api.services.parking_service import ParkingService
    svc = ParkingService(sample_config)
    assert len(svc.slots) == 4
    assert "M-01" in svc.slots
    assert svc.slots["M-01"]["cluster"] == "Merah"

def test_get_slot(sample_config):
    from api.services.parking_service import ParkingService
    svc = ParkingService(sample_config)
    slot = svc.get_slot("M-01")
    assert slot is not None
    assert slot["cluster"] == "Merah"
    assert slot["status"] == "unknown"

def test_get_slot_not_found(sample_config):
    from api.services.parking_service import ParkingService
    svc = ParkingService(sample_config)
    slot = svc.get_slot("NOTFOUND")
    assert slot is None

def test_update_status(sample_config):
    from api.services.parking_service import ParkingService
    svc = ParkingService(sample_config)
    result = svc.update_status("M-01", "terisi")
    assert result is True
    assert svc.slots["M-01"]["status"] == "terisi"

def test_update_status_invalid(sample_config):
    from api.services.parking_service import ParkingService
    svc = ParkingService(sample_config)
    result = svc.update_status("M-01", "invalid")
    assert result is False
    assert svc.slots["M-01"]["status"] == "unknown"

def test_update_status_slot_not_found(sample_config):
    from api.services.parking_service import ParkingService
    svc = ParkingService(sample_config)
    result = svc.update_status("NOTFOUND", "terisi")
    assert result is False

def test_get_slots_by_cluster(sample_config):
    from api.services.parking_service import ParkingService
    svc = ParkingService(sample_config)
    merah_slots = svc.get_slots_by_cluster("Merah")
    assert len(merah_slots) == 2
    assert "M-01" in merah_slots
    assert "M-02" in merah_slots

def test_get_available_slots(sample_config):
    from api.services.parking_service import ParkingService
    svc = ParkingService(sample_config)
    svc.update_status("M-01", "kosong")
    svc.update_status("M-02", "terisi")
    available = svc.get_available_slots("Merah")
    assert len(available) == 1
    assert "M-01" in available
    assert "M-02" not in available

def test_empty_config():
    from api.services.parking_service import ParkingService
    svc = ParkingService("/nonexistent/path.json")
    assert len(svc.slots) == 0