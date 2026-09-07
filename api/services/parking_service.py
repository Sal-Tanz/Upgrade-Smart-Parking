"""Parking slot status management service."""
import json
from typing import Optional

class ParkingService:
    """Service for managing parking slot status."""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.slots: dict[str, dict] = {}
        self._load_config()

    def _load_config(self):
        """Load slot configuration from JSON file."""
        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)
                for slot in config.get("slots", []):
                    slot_id = slot.get("slot_id")
                    if slot_id:
                        self.slots[slot_id] = {
                            "cluster": slot.get("cluster", "Orange"),
                            "status": "unknown",  # unknown, kosong, terisi
                            "polygon": slot.get("polygon", []),
                            "center": slot.get("center", [0, 0]),
                        }
        except (FileNotFoundError, json.JSONDecodeError) as e:
            # Config file doesn't exist or is malformed, start with empty slots
            import logging
            logging.getLogger("parking").warning(f"Slot config error: {e}")

    def get_slot(self, slot_id: str) -> Optional[dict]:
        """Get slot info by ID."""
        return self.slots.get(slot_id)

    def get_all_slots(self) -> dict[str, dict]:
        """Get all slots."""
        return self.slots

    def update_status(self, slot_id: str, status: str) -> bool:
        """Update slot status. Returns True if slot exists."""
        if slot_id in self.slots:
            if status in ("unknown", "kosong", "terisi"):
                self.slots[slot_id]["status"] = status
                return True
        return False

    def get_slots_by_cluster(self, cluster: str) -> list[str]:
        """Get all slot IDs in a cluster."""
        return [sid for sid, info in self.slots.items() if info["cluster"] == cluster]

    def get_available_slots(self, cluster: str) -> list[str]:
        """Get available (kosong) slots in a cluster."""
        return [
            sid for sid, info in self.slots.items()
            if info["cluster"] == cluster and info["status"] == "kosong"
        ]