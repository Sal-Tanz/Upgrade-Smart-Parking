"""Import all models for Alembic autogenerate support."""
from api.models.base import Base
from api.models.vehicle import Vehicle
from api.models.parking_event import ParkingEvent
from api.models.vehicle_schedule import VehicleSchedule
from api.models.attendance_log import AttendanceLog
from api.models.plate_annotation import PlateAnnotation
from api.models.camera_source import CameraSource

__all__ = [
    "Base",
    "Vehicle",
    "ParkingEvent",
    "VehicleSchedule",
    "AttendanceLog",
    "PlateAnnotation",
    "CameraSource",
]