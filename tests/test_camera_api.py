"""Integration tests for camera endpoints."""
import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app
from api.database import get_db


@pytest.mark.asyncio
async def test_camera_api_lifecycle(db):
    """Test full API lifecycle of camera sources."""
    # Override get_db to use test db session
    app.dependency_overrides[get_db] = lambda: db

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # 1. Get initial camera list (empty)
            res = await client.get("/api/cameras")
            assert res.status_code == 200
            data = res.json()
            assert data["total"] == 0
            assert data["cameras"] == []

            # 2. Create RTSP camera
            rtsp_payload = {
                "name": "CCTV Gate Masuk",
                "url": "rtsp://admin:pass@192.168.1.101:554/ch0",
                "location": "Pintu Masuk Utama",
                "is_active": True,
            }
            res_rtsp = await client.post("/api/cameras", json=rtsp_payload)
            assert res_rtsp.status_code == 201
            rtsp_data = res_rtsp.json()
            cam1_id = rtsp_data["id"]
            assert rtsp_data["name"] == "CCTV Gate Masuk"
            assert rtsp_data["resolved_stream_type"] == "rtsp"
            assert rtsp_data["stream_type"] == "rtsp"

            # 3. Create M3U8 camera
            m3u8_payload = {
                "name": "CCTV Area Parkir Barat",
                "url": "https://stream.server.id/live/west_parking.m3u8",
                "location": "Cluster Orange",
                "is_active": True,
            }
            res_m3u8 = await client.post("/api/cameras", json=m3u8_payload)
            assert res_m3u8.status_code == 201
            m3u8_data = res_m3u8.json()
            cam2_id = m3u8_data["id"]
            assert m3u8_data["name"] == "CCTV Area Parkir Barat"
            assert m3u8_data["resolved_stream_type"] == "m3u8"
            assert m3u8_data["stream_type"] == "m3u8"

            # 4. List cameras
            res_list = await client.get("/api/cameras")
            assert res_list.status_code == 200
            assert res_list.json()["total"] == 2

            # 5. Get camera by ID
            res_get = await client.get(f"/api/cameras/{cam1_id}")
            assert res_get.status_code == 200
            assert res_get.json()["name"] == "CCTV Gate Masuk"

            # 6. Update camera
            res_put = await client.put(
                f"/api/cameras/{cam1_id}",
                json={"name": "CCTV Gate Masuk (Renamed)", "location": "Gerbang A"},
            )
            assert res_put.status_code == 200
            assert res_put.json()["name"] == "CCTV Gate Masuk (Renamed)"
            assert res_put.json()["location"] == "Gerbang A"

            # 7. Test stream URL endpoint
            res_test = await client.post(
                "/api/cameras/test",
                json={"url": "rtsp://invalid-test-host:554/test"},
            )
            assert res_test.status_code == 200
            test_res = res_test.json()
            assert test_res["success"] is False
            assert test_res["stream_type"] == "rtsp"

            # 8. Test snapshot endpoint (returns fallback JPEG placeholder for offline camera)
            res_snap = await client.get(f"/api/cameras/{cam1_id}/snapshot")
            assert res_snap.status_code == 200
            assert res_snap.headers["content-type"] == "image/jpeg"
            assert len(res_snap.content) > 100

            # 9. Test rstp:// scheme normalization via API
            rstp_payload = {
                "name": "CCTV Gate Timur Typo",
                "url": "rstp://admin:pass@192.168.1.102:554/live",
                "stream_type": "rstp",
            }
            res_rstp = await client.post("/api/cameras", json=rstp_payload)
            assert res_rstp.status_code == 201
            rstp_res_data = res_rstp.json()
            assert rstp_res_data["url"] == "rtsp://admin:pass@192.168.1.102:554/live"
            assert rstp_res_data["stream_type"] == "rtsp"
            assert rstp_res_data["resolved_stream_type"] == "rtsp"
            cam3_id = rstp_res_data["id"]

            # 10. Validation error on whitespace name or empty url
            res_invalid = await client.post(
                "/api/cameras",
                json={"name": "   ", "url": "rtsp://valid.url/stream"},
            )
            assert res_invalid.status_code == 422

            # 11. Test stream endpoint (returns multipart MJPEG with placeholder chunks)
            res_stream = await client.get(f"/api/cameras/{cam1_id}/stream")
            assert res_stream.status_code == 200
            assert "multipart/x-mixed-replace" in res_stream.headers["content-type"]

            # 12. Test detect endpoint on offline camera (should return 502)
            res_detect = await client.post(f"/api/cameras/{cam1_id}/detect")
            assert res_detect.status_code == 502

            # 13. Delete cameras
            res_del = await client.delete(f"/api/cameras/{cam1_id}")
            assert res_del.status_code == 200
            assert res_del.json()["id"] == cam1_id

            await client.delete(f"/api/cameras/{cam3_id}")

            # 14. Verify 404 after delete
            res_404 = await client.get(f"/api/cameras/{cam1_id}")
            assert res_404.status_code == 404

    finally:
        app.dependency_overrides.pop(get_db, None)

