"""Pydantic schemas for camera sources."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, field_validator


def _normalize_stream_url(v: str) -> str:
    v_clean = v.strip()
    if not v_clean:
        raise ValueError("URL stream tidak boleh kosong")
    if v_clean.lower().startswith("rstp://"):
        return "rtsp://" + v_clean[7:]
    if v_clean.lower().startswith("rstps://"):
        return "rtsps://" + v_clean[8:]
    return v_clean


def _normalize_stream_type_val(v: Optional[str]) -> str:
    if not v:
        return "auto"
    v_lower = v.strip().lower()
    if v_lower == "rstp":
        return "rtsp"
    return v_lower


class CameraSourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Nama kamera")
    url: str = Field(..., min_length=1, max_length=1000, description="URL stream (RTSP, m3u8, HTTP)")
    stream_type: str = Field(default="auto", description="Tipe stream (auto, rtsp, m3u8, http)")
    location: Optional[str] = Field(None, max_length=100, description="Lokasi/area kamera")
    is_active: bool = Field(default=True, description="Status aktif")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v_clean = v.strip()
        if not v_clean:
            raise ValueError("Nama kamera tidak boleh kosong")
        return v_clean

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return _normalize_stream_url(v)

    @field_validator("stream_type")
    @classmethod
    def validate_stream_type(cls, v: Optional[str]) -> str:
        return _normalize_stream_type_val(v)


class CameraSourceCreate(CameraSourceBase):
    pass


class CameraSourceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    url: Optional[str] = Field(None, min_length=1, max_length=1000)
    stream_type: Optional[str] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("name", mode="before")
    @classmethod
    def validate_update_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_clean = v.strip()
            if not v_clean:
                raise ValueError("Nama kamera tidak boleh kosong")
            return v_clean
        return v

    @field_validator("url", mode="before")
    @classmethod
    def validate_update_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return _normalize_stream_url(v)
        return v

    @field_validator("stream_type", mode="before")
    @classmethod
    def validate_update_stream_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return _normalize_stream_type_val(v)
        return v


class CameraSourceResponse(CameraSourceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    resolved_stream_type: str = "http"


class CameraListResponse(BaseModel):
    cameras: List[CameraSourceResponse]
    total: int


class CameraDeleteResponse(BaseModel):
    message: str
    id: int


class CameraTestRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=1000, description="URL stream untuk diuji")
    stream_type: Optional[str] = Field(default="auto", description="Tipe stream")

    @field_validator("url")
    @classmethod
    def validate_test_url(cls, v: str) -> str:
        return _normalize_stream_url(v)

    @field_validator("stream_type")
    @classmethod
    def validate_test_stream_type(cls, v: Optional[str]) -> str:
        return _normalize_stream_type_val(v)


class CameraTestResponse(BaseModel):
    success: bool
    message: str
    stream_type: str
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None

