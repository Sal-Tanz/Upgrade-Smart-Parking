"""Camera service for managing camera sources and video stream handling."""
import asyncio
import os
from typing import AsyncGenerator, Optional
import cv2
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.camera_source import CameraSource


class CameraService:
    """Service for camera source operations and stream processing."""

    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize URL scheme, fixing typos like rstp:// to rtsp://."""
        u = (url or "").strip()
        u_lower = u.lower()
        if u_lower.startswith("rstp://"):
            return "rtsp://" + u[7:]
        if u_lower.startswith("rstps://"):
            return "rtsps://" + u[8:]
        return u

    @staticmethod
    def detect_stream_type(url: str, stream_type: Optional[str] = None) -> str:
        """Detect stream type from URL or explicit type."""
        if stream_type and stream_type.lower() not in ("auto", ""):
            st = stream_type.lower()
            return "rtsp" if st == "rstp" else st
        url_clean = (url or "").strip().lower()
        if url_clean.startswith(("rtsp://", "rtsps://", "rstp://", "rstps://")):
            return "rtsp"
        if ".m3u8" in url_clean:
            return "m3u8"
        if url_clean.isdigit() or url_clean.startswith("/dev/video"):
            return "device"
        return "http"

    async def get_all(
        self, db: AsyncSession, is_active: Optional[bool] = None
    ) -> list[CameraSource]:
        """List all camera sources with optional active filter."""
        stmt = select(CameraSource)
        if is_active is not None:
            stmt = stmt.where(CameraSource.is_active == is_active)
        stmt = stmt.order_by(CameraSource.id.asc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, db: AsyncSession, camera_id: int) -> Optional[CameraSource]:
        """Get camera source by ID."""
        stmt = select(CameraSource).where(CameraSource.id == camera_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, data: dict) -> CameraSource:
        """Create a new camera source."""
        url = self.normalize_url(data["url"])
        stream_type = data.get("stream_type") or "auto"
        if stream_type.lower() in ("auto", ""):
            stream_type = self.detect_stream_type(url)
        elif stream_type.lower() == "rstp":
            stream_type = "rtsp"
        else:
            stream_type = stream_type.lower()

        camera = CameraSource(
            name=data["name"].strip(),
            url=url,
            stream_type=stream_type,
            location=data.get("location"),
            is_active=data.get("is_active", True),
        )
        db.add(camera)
        await db.commit()
        await db.refresh(camera)
        return camera

    async def update(
        self, db: AsyncSession, camera_id: int, data: dict
    ) -> Optional[CameraSource]:
        """Update an existing camera source."""
        camera = await self.get_by_id(db, camera_id)
        if not camera:
            return None

        for key, value in data.items():
            if value is not None and hasattr(camera, key):
                setattr(camera, key, value)

        if "url" in data:
            camera.url = self.normalize_url(data["url"])
            if not data.get("stream_type") or data.get("stream_type") == "auto":
                camera.stream_type = self.detect_stream_type(camera.url)
        if "stream_type" in data and data["stream_type"]:
            st = data["stream_type"].lower()
            camera.stream_type = "rtsp" if st == "rstp" else st

        await db.commit()
        await db.refresh(camera)
        return camera

    async def delete(self, db: AsyncSession, camera_id: int) -> bool:
        """Delete a camera source by ID."""
        camera = await self.get_by_id(db, camera_id)
        if not camera:
            return False
        await db.delete(camera)
        await db.commit()
        return True

    async def test_connection(
        self, url: str, stream_type: str = "auto", timeout: float = 4.0
    ) -> dict:
        """Test stream connection and return resolution/fps info."""
        normalized_url = self.normalize_url(url)
        resolved_type = self.detect_stream_type(normalized_url, stream_type)

        def _sync_test():
            cap = None
            try:
                target = int(normalized_url) if normalized_url.strip().isdigit() else normalized_url.strip()
                if not str(target):
                    return {
                        "success": False,
                        "message": "URL stream tidak boleh kosong",
                        "stream_type": resolved_type,
                    }
                if str(target).lower().startswith(("rtsp://", "rtsps://")):
                    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;3000000"
                else:
                    os.environ.pop("OPENCV_FFMPEG_CAPTURE_OPTIONS", None)
                cap = cv2.VideoCapture(target)
                if not cap.isOpened():
                    return {
                        "success": False,
                        "message": "Gagal membuka koneksi stream (offline atau URL salah)",
                        "stream_type": resolved_type,
                    }
                ret, frame = cap.read()
                if not ret or frame is None:
                    return {
                        "success": False,
                        "message": "Koneksi terbuka tetapi tidak menerima frame video",
                        "stream_type": resolved_type,
                    }
                h, w = frame.shape[:2]
                fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
                fps_text = f", {fps:.1f} fps" if fps > 0 else ""
                return {
                    "success": True,
                    "message": f"Stream terhubung ({w}x{h}{fps_text})",
                    "stream_type": resolved_type,
                    "width": w,
                    "height": h,
                    "fps": round(fps, 1),
                }
            except Exception as exc:
                return {
                    "success": False,
                    "message": f"Koneksi gagal: {str(exc)}",
                    "stream_type": resolved_type,
                }
            finally:
                if cap is not None:
                    cap.release()

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(_sync_test), timeout=timeout + 1.0
            )
        except asyncio.TimeoutError:
            return {
                "success": False,
                "message": f"Koneksi timeout ({timeout}s) - host tidak merespons",
                "stream_type": resolved_type,
            }

    async def capture_frame(self, url: str, timeout: float = 4.0) -> Optional[np.ndarray]:
        """Capture a single frame as a numpy array."""
        normalized_url = self.normalize_url(url)

        def _sync_capture():
            cap = None
            try:
                target = int(normalized_url) if normalized_url.strip().isdigit() else normalized_url.strip()
                if not str(target):
                    return None
                if str(target).lower().startswith(("rtsp://", "rtsps://")):
                    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;3000000"
                else:
                    os.environ.pop("OPENCV_FFMPEG_CAPTURE_OPTIONS", None)
                cap = cv2.VideoCapture(target)
                if not cap.isOpened():
                    return None
                ret, frame = cap.read()
                return frame if ret and frame is not None else None
            except Exception:
                return None
            finally:
                if cap is not None:
                    cap.release()

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(_sync_capture), timeout=timeout + 1.0
            )
        except (asyncio.TimeoutError, Exception):
            return None

    def create_placeholder_image(self, title: str, subtitle: str = "") -> bytes:
        """Generate a dark placeholder JPEG image."""
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        img[:] = (24, 24, 30)  # Dark theme background

        # Background grid pattern
        for y in range(0, 480, 40):
            cv2.line(img, (0, y), (640, y), (35, 35, 42), 1)
        for x in range(0, 640, 40):
            cv2.line(img, (x, 0), (x, 480), (35, 35, 42), 1)

        # Title and Subtitle text
        cv2.putText(
            img,
            title,
            (40, 230),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (240, 240, 240),
            2,
            cv2.LINE_AA,
        )
        if subtitle:
            cv2.putText(
                img,
                subtitle,
                (40, 270),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (140, 140, 180),
                1,
                cv2.LINE_AA,
            )

        _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return buf.tobytes()

    async def generate_mjpeg_stream(
        self, url: str, fps: int = 15
    ) -> AsyncGenerator[bytes, None]:
        """Yield multipart MJPEG chunks for browser streaming."""
        normalized_url = self.normalize_url(url)
        target = int(normalized_url) if normalized_url.strip().isdigit() else normalized_url.strip()
        frame_interval = 1.0 / max(1, min(fps, 30))

        cap = None
        try:
            if str(target).lower().startswith(("rtsp://", "rtsps://")):
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;3000000"
            else:
                os.environ.pop("OPENCV_FFMPEG_CAPTURE_OPTIONS", None)

            cap = await asyncio.to_thread(cv2.VideoCapture, target)
            if not cap.isOpened():
                offline_jpeg = self.create_placeholder_image(
                    "Kamera Tidak Terhubung", "Memeriksa koneksi stream RTSP / m3u8..."
                )
                chunk = (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + offline_jpeg + b"\r\n"
                )
                for _ in range(3):
                    yield chunk
                    await asyncio.sleep(1.0)
                return


            retry_count = 0
            while True:
                start_time = asyncio.get_event_loop().time()
                ret, frame = await asyncio.to_thread(cap.read)

                if not ret or frame is None:
                    retry_count += 1
                    placeholder = self.create_placeholder_image(
                        "Stream Terputus", f"Mencoba menghubungkan kembali ({retry_count})..."
                    )
                    chunk = (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n" + placeholder + b"\r\n"
                    )
                    yield chunk
                    if retry_count > 10:
                        break
                    await asyncio.sleep(1.0)
                    continue

                retry_count = 0
                # Scale down frame if very large to conserve network
                h, w = frame.shape[:2]
                if w > 1280:
                    scale = 1280.0 / w
                    frame = cv2.resize(frame, (1280, int(h * scale)))

                _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                chunk = (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n"
                )
                yield chunk

                elapsed = asyncio.get_event_loop().time() - start_time
                sleep_time = max(0.01, frame_interval - elapsed)
                await asyncio.sleep(sleep_time)

        except asyncio.CancelledError:
            pass
        finally:
            if cap is not None:
                await asyncio.to_thread(cap.release)


camera_service = CameraService()
