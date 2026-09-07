"""Vehicle schemas."""
from pydantic import BaseModel, Field
from datetime import datetime

class VehicleBase(BaseModel):
    """Base vehicle schema."""
    plat: str = Field(..., max_length=20)
    nama_pemilik: str = Field(..., max_length=100)

class VehicleCreate(VehicleBase):
    """Schema for creating a vehicle."""
    jabatan: str = Field(..., pattern="^[DWS]$")

class VehicleUpdate(BaseModel):
    """Schema for updating a vehicle."""
    nama_pemilik: str | None = Field(None, max_length=100)
    jabatan: str | None = Field(None, pattern="^[DWS]$")

class VehicleResponse(VehicleBase):
    """Schema for vehicle response."""
    id: int
    jabatan: str
    cluster: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class VehicleListResponse(BaseModel):
    """Response for listing vehicles."""
    vehicles: list[VehicleResponse]
    total: int

class VehicleDeleteResponse(BaseModel):
    """Response for deleting a vehicle."""
    ok: bool
    message: str = ""
