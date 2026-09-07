export type SlotStatus = "available" | "occupied" | "reserved" | "unknown";

export interface ParkingSlot {
  id: string;
  slot_number: string;
  zone: string;
  status: SlotStatus;
  vehicle_plate?: string;
  last_updated: string;
}

export interface Vehicle {
  id: number;
  plate_number: string;
  owner_name: string;
  vehicle_type: string;
  entry_time: string;
  status: string;
}

export interface ParkingEvent {
  id: number;
  type: "entry" | "exit" | "violation" | "alert";
  timestamp: string;
  vehicle_plate?: string;
  slot_id?: string;
  message: string;
  severity: "info" | "warning" | "error";
}

// Mock parking slots data
export const mockSlots: ParkingSlot[] = [
  { id: "1", slot_number: "A01", zone: "Zone A", status: "available", last_updated: "2024-01-15T10:30:00Z" },
  { id: "2", slot_number: "A02", zone: "Zone A", status: "occupied", vehicle_plate: "B1234XYZ", last_updated: "2024-01-15T10:25:00Z" },
  { id: "3", slot_number: "A03", zone: "Zone A", status: "occupied", vehicle_plate: "D5678ABC", last_updated: "2024-01-15T10:20:00Z" },
  { id: "4", slot_number: "A04", zone: "Zone A", status: "available", last_updated: "2024-01-15T10:15:00Z" },
  { id: "5", slot_number: "A05", zone: "Zone A", status: "reserved", vehicle_plate: "F9012DEF", last_updated: "2024-01-15T10:10:00Z" },
  { id: "6", slot_number: "A06", zone: "Zone A", status: "available", last_updated: "2024-01-15T10:05:00Z" },
  { id: "7", slot_number: "B01", zone: "Zone B", status: "occupied", vehicle_plate: "H3456GHI", last_updated: "2024-01-15T10:00:00Z" },
  { id: "8", slot_number: "B02", zone: "Zone B", status: "available", last_updated: "2024-01-15T09:55:00Z" },
  { id: "9", slot_number: "B03", zone: "Zone B", status: "occupied", vehicle_plate: "J7890JKL", last_updated: "2024-01-15T09:50:00Z" },
  { id: "10", slot_number: "B04", zone: "Zone B", status: "available", last_updated: "2024-01-15T09:45:00Z" },
  { id: "11", slot_number: "B05", zone: "Zone B", status: "occupied", vehicle_plate: "L1234MNO", last_updated: "2024-01-15T09:40:00Z" },
  { id: "12", slot_number: "B06", zone: "Zone B", status: "available", last_updated: "2024-01-15T09:35:00Z" },
  { id: "13", slot_number: "C01", zone: "Zone C", status: "available", last_updated: "2024-01-15T09:30:00Z" },
  { id: "14", slot_number: "C02", zone: "Zone C", status: "occupied", vehicle_plate: "N5678PQR", last_updated: "2024-01-15T09:25:00Z" },
  { id: "15", slot_number: "C03", zone: "Zone C", status: "reserved", vehicle_plate: "P9012STU", last_updated: "2024-01-15T09:20:00Z" },
  { id: "16", slot_number: "C04", zone: "Zone C", status: "available", last_updated: "2024-01-15T09:15:00Z" },
  { id: "17", slot_number: "C05", zone: "Zone C", status: "occupied", vehicle_plate: "R3456VWX", last_updated: "2024-01-15T09:10:00Z" },
  { id: "18", slot_number: "C06", zone: "Zone C", status: "available", last_updated: "2024-01-15T09:05:00Z" },
];

// Mock vehicles data
export const mockVehicles: Vehicle[] = [
  { id: 1, plate_number: "B1234XYZ", owner_name: "John Doe", vehicle_type: "Sedan", entry_time: "2024-01-15T08:00:00Z", status: "parked" },
  { id: 2, plate_number: "D5678ABC", owner_name: "Jane Smith", vehicle_type: "SUV", entry_time: "2024-01-15T08:15:00Z", status: "parked" },
  { id: 3, plate_number: "F9012DEF", owner_name: "Bob Johnson", vehicle_type: "Hatchback", entry_time: "2024-01-15T08:30:00Z", status: "reserved" },
  { id: 4, plate_number: "H3456GHI", owner_name: "Alice Brown", vehicle_type: "Sedan", entry_time: "2024-01-15T08:45:00Z", status: "parked" },
  { id: 5, plate_number: "J7890JKL", owner_name: "Charlie Wilson", vehicle_type: "SUV", entry_time: "2024-01-15T09:00:00Z", status: "parked" },
];

// Mock events data
export const mockEvents: ParkingEvent[] = [
  { id: 1, type: "entry", timestamp: "2024-01-15T10:30:00Z", vehicle_plate: "B1234XYZ", slot_id: "A02", message: "Vehicle entered parking lot", severity: "info" },
  { id: 2, type: "exit", timestamp: "2024-01-15T10:25:00Z", vehicle_plate: "D5678ABC", slot_id: "A03", message: "Vehicle exited parking lot", severity: "info" },
  { id: 3, type: "violation", timestamp: "2024-01-15T10:20:00Z", vehicle_plate: "F9012DEF", slot_id: "A05", message: "Unauthorized vehicle detected in reserved slot", severity: "error" },
  { id: 4, type: "alert", timestamp: "2024-01-15T10:15:00Z", message: "Zone B occupancy at 80%", severity: "warning" },
  { id: 5, type: "entry", timestamp: "2024-01-15T10:10:00Z", vehicle_plate: "H3456GHI", slot_id: "B01", message: "Vehicle entered parking lot", severity: "info" },
];

// Statistics
export const parkingStats = {
  total_slots: 18,
  available_slots: 8,
  occupied_slots: 8,
  reserved_slots: 2,
  occupancy_rate: 55.6,
  today_entries: 12,
  today_exits: 7,
  active_alerts: 1,
};