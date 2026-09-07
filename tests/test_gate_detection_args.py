"""Tests for gate_detection argument parsing."""
import sys
import pytest
from gate_detection import parse_args


def test_parse_args_stream(monkeypatch):
    """Test --stream argument."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["gate_detection.py", "--stream", "rtsp://192.168.1.100:554/live"],
    )
    args = parse_args()
    assert args.stream == "rtsp://192.168.1.100:554/live"
    assert args.video is None
    assert args.camera is None
    assert args.camera_id is None


def test_parse_args_m3u8(monkeypatch):
    """Test --stream with m3u8 link."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["gate_detection.py", "--stream", "https://stream.server/feed.m3u8"],
    )
    args = parse_args()
    assert args.stream == "https://stream.server/feed.m3u8"


def test_parse_args_camera_id(monkeypatch):
    """Test --camera-id argument."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["gate_detection.py", "--camera-id", "3"],
    )
    args = parse_args()
    assert args.camera_id == 3
    assert args.stream is None


def test_parse_args_rstp(monkeypatch):
    """Test --stream with rstp typo."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["gate_detection.py", "--stream", "rstp://192.168.1.50:554/live"],
    )
    args = parse_args()
    assert args.stream == "rstp://192.168.1.50:554/live"


def test_open_source_rstp_normalization(monkeypatch):
    """Test open_source handles rstp scheme and TCP options."""
    import os
    from gate_detection import open_source
    # Test open_source on non-existent stream returns None gracefully
    cap = open_source("rstp://127.0.0.1:65530/test")
    assert cap is None
    assert "rtsp_transport;tcp" in os.environ.get("OPENCV_FFMPEG_CAPTURE_OPTIONS", "")

