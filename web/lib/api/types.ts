/**
 * Type definitions untuk Smart Parking System
 *
 * Field names disesuaikan dengan backend API responses
 */

export interface Vehicle {
  plat: string;
  plate?: string;
  nama_pemilik?: string;
  owner?: string;
  jabatan?: string; // "D" (Dekan), "W" (Wakil Dekan), "S" (Staff)
  role?: string;
  cluster_hak?: string; // "Merah" atau "Orange"
  cluster?: string;
  aktif?: boolean;
  status?: string; // "active" | "inactive" | "aktif" | "nonaktif"
  created_at?: string;
  updated_at?: string;
}

export interface ParkingSlot {
  slot_id: string;
  cluster: string; // "Merah" atau "Orange"
  status: string; // "available", "occupied", "reserved", "unknown", "kosong", "terisi"
  vehicle_plat?: string;
  polygon?: number[][];
  center?: number[];
}

export interface ParkingEvent {
  id: number;
  plat?: string;
  plate?: string;
  plate_number?: string;
  event_type: string;
  type?: string;
  slot_id?: string;
  cluster?: string;
  violation_type?: string;
  expected_cluster?: string;
  actual_cluster?: string;
  reason?: string;
  validation_result?: string;
  buzzer_pattern?: string;
  buzzer?: string;
  is_valid?: boolean;
  status?: string;
  resolved?: boolean;
  jabatan?: string;
  created_at?: string;
  timestamp?: string;
}

export interface StatsData {
  total_slots: number;
  available_slots: number;
  occupied_slots: number;
  reserved_slots: number;
  active_vehicles: number;
  today_events: number;
}

export interface ValidationResult {
  is_valid: boolean;
  slot_id: string;
  expected_cluster?: string;
  actual_cluster?: string;
  violation_type?: string;
  reason: string;
  buzzer_pattern: string;
}

export interface PlateValidationResult {
  status: string; // "ACCEPTED", "REJECTED"
  plat: string;
  jabatan?: string;
  cluster?: string;
  reason?: string;
  buzzer_pattern?: string;
}

export interface AttendanceRecord {
  id: string | number;
  plate_number: string;
  plate?: string;
  vehicle_id?: number;
  entry_time?: string;
  exit_time?: string;
  arrival_time?: string;
  departure_time?: string;
  date?: string;
  duration_minutes?: number;
  parking_duration_minutes?: number;
  slot_id?: string;
  arrival_status?: string;
  departure_status?: string;
  status: "active" | "completed" | string;
}

