import type { ParkingEvent, ParkingSlot } from '@/lib/api/types';

export interface DashboardStats {
  total_slots: number;
  available_slots: number;
  occupied_slots: number;
  reserved_slots: number;
  active_vehicles: number;
  today_events: number;
}

export function calculateDashboardStats(
  slots: ParkingSlot[],
  events: ParkingEvent[],
  now = new Date(),
): DashboardStats {
  const available_slots = slots.filter((slot) => slot.status === 'available' || slot.status === 'kosong').length;
  const occupied_slots = slots.filter((slot) => slot.status === 'occupied' || slot.status === 'terisi').length;
  const reserved_slots = slots.filter((slot) => slot.status === 'reserved').length;

  const todayStart = new Date(now);
  todayStart.setHours(0, 0, 0, 0);
  const tomorrowStart = new Date(todayStart);
  tomorrowStart.setDate(tomorrowStart.getDate() + 1);

  const today_events = events.filter((event) => {
    const eventTime = event.created_at || event.timestamp;
    if (!eventTime) return false;
    const createdAt = new Date(eventTime);
    return !isNaN(createdAt.getTime()) && createdAt >= todayStart && createdAt < tomorrowStart;
  }).length;

  return {
    total_slots: slots.length,
    available_slots,
    occupied_slots,
    reserved_slots,
    active_vehicles: 0,
    today_events,
  };
}
