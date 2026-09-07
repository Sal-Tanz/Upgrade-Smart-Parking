"""Unit tests for CameraService."""
import pytest
from api.models.camera_source import CameraSource
from api.services.camera_service import camera_service


def test_detect_stream_type():
    """Test automatic detection of stream types."""
    assert camera_service.detect_stream_type("rtsp://admin:pass@192.168.1.50:554/live") == "rtsp"
    assert camera_service.detect_stream_type("RTSP://10.0.0.1/ch0") == "rtsp"
    assert camera_service.detect_stream_type("rtsps://secure-cam.local/stream") == "rtsp"
    # Indonesian / typo rstp:// and rstps://
    assert camera_service.detect_stream_type("rstp://admin:pass@192.168.1.50:554/live") == "rtsp"
    assert camera_service.detect_stream_type("RSTP://10.0.0.1/ch0") == "rtsp"
    assert camera_service.detect_stream_type("rstps://secure-cam.local/stream") == "rtsp"
    assert camera_service.detect_stream_type("http://stream.server.com/live/index.m3u8") == "m3u8"
    assert camera_service.detect_stream_type("https://video.org/camera1.m3u8?auth=123") == "m3u8"
    assert camera_service.detect_stream_type("0") == "device"
    assert camera_service.detect_stream_type("/dev/video0") == "device"
    assert camera_service.detect_stream_type("http://192.168.1.10/video.mjpeg") == "http"
    # Explicit stream_type overrides auto-detection
    assert camera_service.detect_stream_type("http://any-url.com", stream_type="rtsp") == "rtsp"
    assert camera_service.detect_stream_type("http://any-url.com", stream_type="rstp") == "rtsp"
    assert camera_service.detect_stream_type("rtsp://any-url.com", stream_type="m3u8") == "m3u8"


def test_normalize_url():
    """Test normalizing rstp typos to rtsp."""
    assert camera_service.normalize_url("rstp://192.168.1.100:554/live") == "rtsp://192.168.1.100:554/live"
    assert camera_service.normalize_url("RSTP://cam.local/live") == "rtsp://cam.local/live"
    assert camera_service.normalize_url("rstps://cam.local/live") == "rtsps://cam.local/live"
    assert camera_service.normalize_url("rtsp://cam.local/live") == "rtsp://cam.local/live"
    assert camera_service.normalize_url("https://stream.id/live.m3u8") == "https://stream.id/live.m3u8"



@pytest.mark.asyncio
async def test_camera_crud(db):
    """Test full CRUD lifecycle for camera sources."""
    # 1. Create RTSP camera
    cam1 = await camera_service.create(
        db,
        {
            "name": "Gerbang Utama",
            "url": "rtsp://192.168.1.100:554/live",
            "location": "Pintu Masuk",
            "is_active": True,
        },
    )
    assert cam1.id is not None
    assert cam1.name == "Gerbang Utama"
    assert cam1.url == "rtsp://192.168.1.100:554/live"
    assert cam1.stream_type == "rtsp"
    assert cam1.resolved_stream_type == "rtsp"

    # 2. Create M3U8 camera
    cam2 = await camera_service.create(
        db,
        {
            "name": "Area Parkir Cluster Merah",
            "url": "https://streams.smartparking.id/hls/cluster_merah.m3u8",
            "location": "Cluster Merah",
            "is_active": False,
        },
    )
    assert cam2.id is not None
    assert cam2.name == "Area Parkir Cluster Merah"
    assert cam2.stream_type == "m3u8"
    assert cam2.resolved_stream_type == "m3u8"

    # 3. Get all
    all_cams = await camera_service.get_all(db)
    assert len(all_cams) == 2

    active_cams = await camera_service.get_all(db, is_active=True)
    assert len(active_cams) == 1
    assert active_cams[0].name == "Gerbang Utama"

    # 4. Get by ID
    fetched = await camera_service.get_by_id(db, cam1.id)
    assert fetched is not None
    assert fetched.name == "Gerbang Utama"

    # 5. Update
    updated = await camera_service.update(
        db, cam1.id, {"name": "Gerbang Masuk Rev", "url": "https://stream.local/feed.m3u8"}
    )
    assert updated is not None
    assert updated.name == "Gerbang Masuk Rev"
    assert updated.stream_type == "m3u8"

    # 6. Delete
    deleted = await camera_service.delete(db, cam1.id)
    assert deleted is True

    remaining = await camera_service.get_all(db)
    assert len(remaining) == 1
    assert remaining[0].id == cam2.id

    # 7. Delete non-existent
    assert await camera_service.delete(db, 99999) is False


@pytest.mark.asyncio
async def test_camera_rstp_typo_and_long_url(db):
    """Test that rstp:// scheme typo is normalized and long stream URLs (>255 chars) work."""
    long_url = (
        "https://video-edge.smartparking.id/hls/camera_gate_east/stream.m3u8?"
        + "token=" + "a" * 260
    )
    assert len(long_url) > 300

    # 1. Test rstp:// input
    cam = await camera_service.create(
        db,
        {
            "name": "Kamera RSTP Typo",
            "url": "rstp://admin:secret@192.168.1.200:554/live",
            "stream_type": "rstp",
        },
    )
    assert cam.url == "rtsp://admin:secret@192.168.1.200:554/live"
    assert cam.stream_type == "rtsp"
    assert cam.resolved_stream_type == "rtsp"

    # 2. Test long URL update
    updated = await camera_service.update(db, cam.id, {"url": long_url})
    assert updated.url == long_url
    assert updated.resolved_stream_type == "m3u8"



@pytest.mark.asyncio
async def test_test_connection_invalid_url():
    """Test that an unreachable URL fails gracefully without unhandled exception."""
    result = await camera_service.test_connection("rtsp://256.256.256.256:554/invalid", timeout=1.0)
    assert result["success"] is False
    assert "stream_type" in result
    assert result["stream_type"] == "rtsp"


def test_create_placeholder_image():
    """Test generating offline placeholder JPEG image."""
    img_bytes = camera_service.create_placeholder_image("Kamera Offline", "Testing...")
    assert isinstance(img_bytes, bytes)
    assert len(img_bytes) > 100
    # Check JPEG magic header
    assert img_bytes[:2] == b"\xff\xd8"
