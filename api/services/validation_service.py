"""Validation service — plate validation + K-Map cluster checking."""
from sqlalchemy.ext.asyncio import AsyncSession
from logic.karnaugh import compute_cluster, validate_cluster_access
from api.services.vehicle_service import VehicleService
from api.services.parking_service import ParkingService


class ValidationService:
    """Orchestrates plate validation and parking validation."""

    def __init__(
        self,
        vehicle_svc: VehicleService,
        parking_svc: ParkingService,
        allow_merah_to_orange_fallback: bool = True,
    ):
        self.vehicle_svc = vehicle_svc
        self.parking_svc = parking_svc
        self.allow_fallback = allow_merah_to_orange_fallback

    async def validate_plate(self, db: AsyncSession, plate_text: str) -> dict:
        """Check if plate is registered and determine cluster access."""
        normalized = plate_text.strip().upper()
        vehicle = await self.vehicle_svc.get_by_plate(db, normalized)

        if vehicle is None:
            return {
                "is_registered": False,
                "status": "REJECTED",
                "plate_text": normalized,
                "jabatan": None,
                "cluster": None,
                "reason": "Plat tidak terdaftar",
                "buzzer_pattern": "LONG_3X",
            }

        if not vehicle.aktif:
            return {
                "is_registered": True,
                "status": "REJECTED",
                "plate_text": normalized,
                "jabatan": vehicle.jabatan,
                "cluster": None,
                "reason": "Kendaraan tidak aktif",
                "buzzer_pattern": "LONG_3X",
            }

        cluster = compute_cluster(vehicle.jabatan)

        return {
            "is_registered": True,
            "status": "ACCEPTED",
            "plate_text": normalized,
            "jabatan": vehicle.jabatan,
            "cluster": cluster,
            "reason": "Kendaraan terdaftar",
            "buzzer_pattern": "SUCCESS_TONE",
        }

    async def validate_parking(
        self, db: AsyncSession, plate_text: str, slot_id: str
    ) -> dict:
        """Full parking validation: plate check + slot availability + K-Map."""
        normalized = plate_text.strip().upper()

        plate_result = await self.validate_plate(db, normalized)
        if not plate_result["is_registered"]:
            return {
                "is_valid": False,
                "violation_type": "UNREGISTERED",
                "slot_id": slot_id,
                "reason": plate_result["reason"],
                "buzzer_pattern": plate_result["buzzer_pattern"],
                "expected_cluster": None,
                "actual_cluster": None,
            }

        if plate_result["status"] != "ACCEPTED":
            return {
                "is_valid": False,
                "violation_type": "INACTIVE_VEHICLE",
                "slot_id": slot_id,
                "reason": plate_result["reason"],
                "buzzer_pattern": plate_result["buzzer_pattern"],
                "expected_cluster": None,
                "actual_cluster": None,
            }

        vehicle = await self.vehicle_svc.get_by_plate(db, normalized)
        expected_cluster = plate_result["cluster"]

        slot = self.parking_svc.get_slot(slot_id)
        if slot is None:
            return {
                "is_valid": False,
                "violation_type": "INVALID_SLOT",
                "slot_id": slot_id,
                "reason": f"Slot ID tidak valid: {slot_id}",
                "buzzer_pattern": "MEDIUM_2X",
                "expected_cluster": expected_cluster,
                "actual_cluster": None,
            }

        actual_cluster = slot["cluster"]

        # A slot must be explicitly marked available before a vehicle can occupy it.
        if slot.get("status") != "kosong":
            return {
                "is_valid": False,
                "violation_type": "OCCUPIED_SLOT",
                "slot_id": slot_id,
                "reason": "Slot parkir tidak tersedia",
                "buzzer_pattern": "MEDIUM_2X",
                "expected_cluster": expected_cluster,
                "actual_cluster": actual_cluster,
            }

        is_valid = validate_cluster_access(
            vehicle.jabatan,
            actual_cluster,
            allow_merah_to_orange_fallback=self.allow_fallback,
        )

        if is_valid:
            return {
                "is_valid": True,
                "violation_type": "NONE",
                "slot_id": slot_id,
                "reason": "Parkir valid",
                "buzzer_pattern": "SUCCESS_TONE",
                "expected_cluster": expected_cluster,
                "actual_cluster": actual_cluster,
            }

        return {
            "is_valid": False,
            "violation_type": "WRONG_CLUSTER",
            "slot_id": slot_id,
            "reason": (
                f"Kendaraan {vehicle.jabatan} parkir di cluster {actual_cluster}, "
                f"seharusnya di cluster {expected_cluster}"
            ),
            "buzzer_pattern": "MEDIUM_2X",
            "expected_cluster": expected_cluster,
            "actual_cluster": actual_cluster,
        }
