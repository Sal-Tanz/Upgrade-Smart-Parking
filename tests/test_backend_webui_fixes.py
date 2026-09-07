"""Regression tests for backend and Web UI synchronization fixes."""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from fastapi import HTTPException
from httpx import AsyncClient, ASGITransport

from api.main import app
from api.database import get_db
from api.models.attendance_log import AttendanceLog
from api.models.vehicle import Vehicle
from api.services.mqtt_service import MQTTService
from api.services.parking_service import ParkingService
from api.routes.detection import _get_pipeline


@pytest.mark.asyncio
async def test_attendance_log_to_dict_enrichment(db):
    """Test that AttendanceLog.to_dict() provides Web UI friendly alias fields."""
    # Create vehicle
    vehicle = Vehicle(
        plat="B 1234 TEST",
        nama_pemilik="Budi Santoso",
        jabatan="D",
        cluster_hak="Merah",
        aktif=True,
    )
    db.add(vehicle)
    await db.commit()
    await db.refresh(vehicle)

    # Create attendance log
    arr_time = datetime(2026, 9, 7, 8, 0, 0, tzinfo=timezone.utc)
    dep_time = datetime(2026, 9, 7, 16, 30, 0, tzinfo=timezone.utc)
    log = AttendanceLog(
        vehicle_id=vehicle.id,
        date="2026-09-07",
        arrival_time=arr_time,
        departure_time=dep_time,
        arrival_status="TEPAT_WAKTU",
        departure_status="TEPAT_WAKTU",
        parking_duration_minutes=510,
    )
    log.vehicle = vehicle
    db.add(log)
    await db.commit()
    await db.refresh(log)

    data = log.to_dict()
    assert data["plate_number"] == "B 1234 TEST"
    assert data["entry_time"] is not None
    assert data["exit_time"] is not None
    assert data["duration_minutes"] == 510
    assert data["status"] == "completed"


@pytest.mark.asyncio
async def test_slot_put_endpoint():
    """Test PUT /api/slots/{slot_id} endpoint."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Update slot M-01 to occupied
        res = await client.put("/api/slots/M-01?status=terisi")
        assert res.status_code == 200
        json_data = res.json()
        assert json_data["slot_id"] == "M-01"
        assert json_data["status"] == "terisi"

        # Update slot M-01 back to available (kosong)
        res2 = await client.put("/api/slots/M-01?status=available")
        assert res2.status_code == 200
        json_data2 = res2.json()
        assert json_data2["status"] == "kosong"

        # Update non-existent slot
        res_404 = await client.put("/api/slots/NON_EXISTENT?status=kosong")
        assert res_404.status_code == 404


def test_mqtt_v2_disconnect_signature():
    """Test that _on_disconnect handles Paho-MQTT v2 5-parameter callback safely."""
    mqtt_svc = MQTTService()
    # Paho-MQTT v2 calls on_disconnect(client, userdata, disconnect_flags, reason_code, properties)
    fake_client = MagicMock()
    fake_userdata = None
    fake_disconnect_flags = MagicMock()
    fake_reason_code = 0
    fake_properties = MagicMock()

    # Must not raise TypeError
    mqtt_svc._on_disconnect(
        fake_client,
        fake_userdata,
        fake_disconnect_flags,
        fake_reason_code,
        fake_properties,
    )
    assert mqtt_svc.connected is False


def test_detection_pipeline_import_error_handling(monkeypatch):
    """Test that _get_pipeline raises HTTPException 503 if ML engine is missing."""
    import api.routes.detection as det_mod

    def mock_init_fail():
        raise ImportError("Mocked OCR engine missing")

    monkeypatch.setattr(det_mod, "_pipeline", None)
    monkeypatch.setattr(det_mod, "ALPRPipeline", mock_init_fail)

    with pytest.raises(HTTPException) as exc_info:
        det_mod._get_pipeline()
    assert exc_info.value.status_code == 503
