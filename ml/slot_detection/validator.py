"""
Modul Validasi Posisi Kendaraan Parkir.

Tujuan:
    - Memvalidasi apakah kendaraan parkir di cluster yang sesuai dengan hak akses
    - Menggunakan logika Karnaugh Map dari logic/karnaugh.py
    - Trigger buzzer/notifikasi jika terjadi pelanggaran

Logika:
    - Dekan (D) & Wakil Dekan (W) → Cluster Merah (boleh fallback ke Orange)
    - Dosen (S) → Cluster Orange
    - Tamu/tidak terdaftar → Tidak boleh parkir

Penggunaan:
    from ml.slot_detection.validator import ParkingValidator
    
    validator = ParkingValidator(slot_config_path="data/slot_config.json")
    
    # Validasi posisi parkir
    result = validator.validate(
        plate_text="B 1234 XYZ",
        slot_id="M-01",
        jabatan="D"
    )
    
    if result.is_valid:
        print("✅ Parkir valid")
    else:
        print(f"❌ Pelanggaran: {result.reason}")
        # Trigger buzzer warning
"""

import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from loguru import logger

# Import logika Karnaugh Map menggunakan importlib untuk menghindari sys.path hack
import importlib.util

_karnaugh_path = Path(__file__).resolve().parent.parent.parent / "logic" / "karnaugh.py"
_spec = importlib.util.spec_from_file_location("karnaugh", _karnaugh_path)
_karnaugh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_karnaugh)

compute_cluster = _karnaugh.compute_cluster
validate_cluster_access = _karnaugh.validate_cluster_access


class ViolationType(Enum):
    """Jenis pelanggaran parkir."""
    NONE = "NONE"                      # Tidak ada pelanggaran
    WRONG_CLUSTER = "WRONG_CLUSTER"    # Parkir di cluster yang salah
    UNREGISTERED = "UNREGISTERED"      # Kendaraan tidak terdaftar
    CLUSTER_FULL = "CLUSTER_FULL"      # Cluster yang berhak sudah penuh
    INVALID_SLOT = "INVALID_SLOT"      # Slot ID tidak valid


class BuzzerPattern(Enum):
    """Pola buzzer untuk notifikasi."""
    NONE = "NONE"
    SUCCESS_TONE = "SUCCESS_TONE"      # Bip naik singkat (valid)
    SHORT_1X = "SHORT_1X"              # Bip pendek sekali (retry)
    MEDIUM_2X = "MEDIUM_2X"            # Bip sedang 2x (wrong cluster)
    LONG_3X = "LONG_3X"                # Bip panjang 3x (unregistered)
    SHORT_DOUBLE = "SHORT_DOUBLE"      # 2 bip cepat (cluster full)


@dataclass
class ValidationResult:
    """Hasil validasi posisi parkir."""
    is_valid: bool
    plate_text: str
    slot_id: str
    jabatan: Optional[str]
    expected_cluster: Optional[str]    # Cluster yang seharusnya
    actual_cluster: Optional[str]      # Cluster slot yang digunakan
    violation_type: ViolationType
    reason: str
    buzzer_pattern: BuzzerPattern
    allow_fallback: bool = False       # Apakah boleh fallback ke cluster lain


class ParkingValidator:
    """
    Validasi posisi kendaraan parkir.

    Args:
        slot_config_path: Path ke JSON konfigurasi slot
        allow_merah_to_orange_fallback: Izinkan Dekan/WD parkir di Orange jika Merah penuh
    """

    def __init__(
        self,
        slot_config_path: str = "data/slot_config.json",
        allow_merah_to_orange_fallback: bool = True,
    ):
        self.slot_config_path = slot_config_path
        self.allow_fallback = allow_merah_to_orange_fallback
        
        # Load slot configuration
        self.slots = self._load_slot_config()
        
        logger.info(
            f"ParkingValidator siap | "
            f"slots_loaded={len(self.slots)} | "
            f"fallback_enabled={allow_merah_to_orange_fallback}"
        )

    def _load_slot_config(self) -> dict:
        """Load konfigurasi slot dari JSON."""
        config_path = Path(self.slot_config_path)
        
        if not config_path.exists():
            logger.warning(
                f"Slot config tidak ditemukan: {self.slot_config_path}. "
                "Menggunakan empty config."
            )
            return {}

        with open(config_path, "r") as f:
            config = json.load(f)

        # Convert ke dict dengan slot_id sebagai key
        slots_dict = {}
        for slot in config.get("slots", []):
            slot_id = slot.get("slot_id")
            if slot_id:
                slots_dict[slot_id] = slot

        logger.info(f"Loaded {len(slots_dict)} slots from config")
        return slots_dict

    def validate(
        self,
        plate_text: str,
        slot_id: str,
        jabatan: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validasi apakah kendaraan boleh parkir di slot tertentu.

        Args:
            plate_text: Teks plat nomor kendaraan
            slot_id: ID slot parkir yang digunakan
            jabatan: Kode jabatan (D/W/S) atau None jika tidak terdaftar

        Returns:
            ValidationResult berisi status validasi dan rekomendasi aksi
        """
        logger.debug(
            f"Validating: plate={plate_text}, slot={slot_id}, jabatan={jabatan}"
        )

        # Check 1: Apakah slot ID valid?
        if slot_id not in self.slots:
            logger.warning(f"Slot ID tidak valid: {slot_id}")
            return ValidationResult(
                is_valid=False,
                plate_text=plate_text,
                slot_id=slot_id,
                jabatan=jabatan,
                expected_cluster=None,
                actual_cluster=None,
                violation_type=ViolationType.INVALID_SLOT,
                reason=f"Slot ID tidak valid: {slot_id}",
                buzzer_pattern=BuzzerPattern.MEDIUM_2X,
            )

        # Check 2: Apakah kendaraan terdaftar?
        if jabatan is None:
            logger.warning(f"Kendaraan tidak terdaftar: {plate_text}")
            return ValidationResult(
                is_valid=False,
                plate_text=plate_text,
                slot_id=slot_id,
                jabatan=None,
                expected_cluster=None,
                actual_cluster=self.slots[slot_id].get("cluster"),
                violation_type=ViolationType.UNREGISTERED,
                reason=f"Kendaraan tidak terdaftar: {plate_text}",
                buzzer_pattern=BuzzerPattern.LONG_3X,
            )

        # Check 3: Hitung cluster yang seharusnya menggunakan Karnaugh Map
        expected_cluster = compute_cluster(jabatan)
        
        if expected_cluster is None:
            logger.warning(f"Jabatan tidak valid: {jabatan}")
            return ValidationResult(
                is_valid=False,
                plate_text=plate_text,
                slot_id=slot_id,
                jabatan=jabatan,
                expected_cluster=None,
                actual_cluster=self.slots[slot_id].get("cluster"),
                violation_type=ViolationType.UNREGISTERED,
                reason=f"Jabatan tidak valid: {jabatan}",
                buzzer_pattern=BuzzerPattern.LONG_3X,
            )

        # Check 4: Dapatkan cluster slot yang digunakan
        actual_cluster = self.slots[slot_id].get("cluster")

        # Check 5: Validasi menggunakan logika Karnaugh Map
        is_valid = validate_cluster_access(
            jabatan, actual_cluster, allow_merah_to_orange_fallback=self.allow_fallback
        )

        if is_valid:
            # Valid! Parkir di cluster yang benar
            logger.info(
                f"✅ VALID: {plate_text} ({jabatan}) parkir di {slot_id} ({actual_cluster})"
            )
            return ValidationResult(
                is_valid=True,
                plate_text=plate_text,
                slot_id=slot_id,
                jabatan=jabatan,
                expected_cluster=expected_cluster,
                actual_cluster=actual_cluster,
                violation_type=ViolationType.NONE,
                reason="Parkir valid",
                buzzer_pattern=BuzzerPattern.SUCCESS_TONE,
                allow_fallback=(expected_cluster != actual_cluster),
            )
        else:
            # Invalid! Parkir di cluster yang salah
            logger.warning(
                f"❌ VIOLATION: {plate_text} ({jabatan}) parkir di {slot_id} ({actual_cluster}), "
                f"seharusnya di {expected_cluster}"
            )
            return ValidationResult(
                is_valid=False,
                plate_text=plate_text,
                slot_id=slot_id,
                jabatan=jabatan,
                expected_cluster=expected_cluster,
                actual_cluster=actual_cluster,
                violation_type=ViolationType.WRONG_CLUSTER,
                reason=(
                    f"Kendaraan {jabatan} parkir di cluster {actual_cluster}, "
                    f"seharusnya di cluster {expected_cluster}"
                ),
                buzzer_pattern=BuzzerPattern.MEDIUM_2X,
            )

    def find_available_slots(
        self,
        jabatan: str,
        occupied_slots: set[str],
    ) -> list[str]:
        """
        Cari slot kosong yang sesuai dengan hak akses jabatan.

        Args:
            jabatan: Kode jabatan (D/W/S)
            occupied_slots: Set slot ID yang sudah terisi

        Returns:
            List slot ID yang kosong dan sesuai hak akses,
            diurutkan berdasarkan prioritas (Merah dulu, baru Orange)
        """
        expected_cluster = compute_cluster(jabatan)
        
        if expected_cluster is None:
            return []

        available = []

        # Cari slot di cluster yang sesuai
        for slot_id, slot in self.slots.items():
            if slot_id in occupied_slots:
                continue  # Skip yang sudah terisi

            slot_cluster = slot.get("cluster")
            
            # Check apakah jabatan boleh parkir di slot ini
            if validate_cluster_access(jabatan, slot_cluster):
                available.append(slot_id)

        # Sort: prioritaskan cluster Merah dulu (untuk Dekan/WD)
        def sort_key(slot_id):
            slot_cluster = self.slots[slot_id].get("cluster")
            return (0 if slot_cluster == "Merah" else 1, slot_id)

        available.sort(key=sort_key)

        logger.debug(
            f"Available slots for {jabatan}: {len(available)} "
            f"(first 5: {available[:5]})"
        )

        return available

    def get_slot_status_summary(self, occupied_slots: set[str]) -> dict:
        """
        Dapatkan ringkasan status semua slot.

        Args:
            occupied_slots: Set slot ID yang sudah terisi

        Returns:
            Dict berisi statistik slot
        """
        total = len(self.slots)
        occupied = len(occupied_slots)
        available = total - occupied

        # Hitung per cluster
        merah_total = sum(1 for s in self.slots.values() if s.get("cluster") == "Merah")
        merah_occupied = sum(
            1 for slot_id in occupied_slots
            if slot_id in self.slots and self.slots[slot_id].get("cluster") == "Merah"
        )
        merah_available = merah_total - merah_occupied

        orange_total = sum(1 for s in self.slots.values() if s.get("cluster") == "Orange")
        orange_occupied = sum(
            1 for slot_id in occupied_slots
            if slot_id in self.slots and self.slots[slot_id].get("cluster") == "Orange"
        )
        orange_available = orange_total - orange_occupied

        summary = {
            "total_slots": total,
            "occupied": occupied,
            "available": available,
            "merah": {
                "total": merah_total,
                "occupied": merah_occupied,
                "available": merah_available,
            },
            "orange": {
                "total": orange_total,
                "occupied": orange_occupied,
                "available": orange_available,
            },
        }

        return summary


# Convenience function untuk quick validation
def quick_validate(
    plate_text: str,
    slot_id: str,
    jabatan: Optional[str],
    slot_config_path: str = "data/slot_config.json",
) -> ValidationResult:
    """
    Quick validation function.

    Args:
        plate_text: Teks plat nomor
        slot_id: ID slot
        jabatan: Kode jabatan
        slot_config_path: Path ke slot config

    Returns:
        ValidationResult
    """
    validator = ParkingValidator(slot_config_path)
    return validator.validate(plate_text, slot_id, jabatan)


if __name__ == "__main__":
    # Contoh penggunaan
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: python validator.py <plate_text> <slot_id> <jabatan>")
        print("Example: python validator.py 'B 1234 XYZ' 'M-01' 'D'")
        sys.exit(1)

    plate_text = sys.argv[1]
    slot_id = sys.argv[2]
    jabatan = sys.argv[3] if sys.argv[3] != "None" else None

    result = quick_validate(plate_text, slot_id, jabatan)

    print("\n" + "=" * 60)
    print("PARKING VALIDATION RESULT")
    print("=" * 60)
    print(f"Plate:              {result.plate_text}")
    print(f"Slot:               {result.slot_id}")
    print(f"Jabatan:            {result.jabatan}")
    print(f"Expected Cluster:   {result.expected_cluster}")
    print(f"Actual Cluster:     {result.actual_cluster}")
    print(f"Valid:              {'✅ YES' if result.is_valid else '❌ NO'}")
    print(f"Violation Type:     {result.violation_type.value}")
    print(f"Reason:             {result.reason}")
    print(f"Buzzer Pattern:     {result.buzzer_pattern.value}")
    print("=" * 60)