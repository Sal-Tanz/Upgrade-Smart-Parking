'use client';

import { useEffect, useMemo, useState } from 'react';
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { StatsCard } from "@/components/dashboard/stats-card";
import { ParkingGrid } from "@/components/dashboard/parking-grid";
import { EventList } from "@/components/dashboard/event-list";
import { useWebSocket } from '@/lib/hooks/useWebSocket';
import { parkingApi, eventApi } from '@/lib/api/client';
import type { ParkingEvent, ParkingSlot, StatsData } from '@/lib/api/types';
import { calculateDashboardStats } from '@/lib/dashboard/stats';
import { ParkingSquare, TrendingUp, AlertTriangle } from "lucide-react";

function getDefaultWebSocketUrl(): string {
  if (process.env.NEXT_PUBLIC_WS_URL) {
    return process.env.NEXT_PUBLIC_WS_URL;
  }

  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}/api/events/ws/events`;
  }

  return 'ws://localhost:8000/api/events/ws/events';
}

export default function DashboardPage() {
  const [slots, setSlots] = useState<ParkingSlot[]>([]);
  const [events, setEvents] = useState<ParkingEvent[]>([]);
  const [stats, setStats] = useState<StatsData>({
    total_slots: 0, available_slots: 0, occupied_slots: 0,
    reserved_slots: 0, active_vehicles: 0, today_events: 0,
  });
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [error, setError] = useState<string | null>(null);

  const wsUrl = useMemo(() => getDefaultWebSocketUrl(), []);
  const { connectionStatus } = useWebSocket({
    url: wsUrl,
    onMessage: (data) => {
      const eventType = data?.event_type || data?.type;
      if (data && eventType) {
        const normalized: ParkingEvent = {
          id: data.id || Date.now(),
          event_type: eventType,
          type: eventType,
          plat: data.plat || data.plate_number || data.plate || "",
          plate_number: data.plate_number || data.plat || data.plate || "",
          slot_id: data.slot_id,
          cluster: data.cluster,
          jabatan: data.jabatan,
          reason: data.reason || data.validation_result || `Event ${eventType}`,
          validation_result: data.validation_result || data.reason || "",
          buzzer_pattern: data.buzzer_pattern || data.buzzer || "",
          created_at: data.created_at || data.timestamp || new Date().toISOString(),
          timestamp: data.timestamp || data.created_at || new Date().toISOString(),
          is_valid: data.is_valid ?? (eventType !== "VIOLATION" && data.validation_result !== "REJECTED"),
        };
        setEvents(prev => [normalized, ...prev].slice(0, 50));
      }
    },
  });

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        setError(null);

        const [slotsRes, eventsRes] = await Promise.all([
          parkingApi.getAll(),
          eventApi.getAll({ limit: 50 }),
        ]);

        const fetchedSlots = slotsRes.success && slotsRes.data ? slotsRes.data : [];
        const fetchedEvents = eventsRes.success && eventsRes.data ? eventsRes.data : [];

        setSlots(fetchedSlots);
        setEvents(fetchedEvents);
        setStats(calculateDashboardStats(fetchedSlots, fetchedEvents));

        const failures = [slotsRes, eventsRes].filter((result) => !result.success);
        if (failures.length > 0) {
          setError(failures.map((result) => result.error).filter(Boolean).join('; ') || 'Failed to load dashboard data');
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load dashboard data';
        setError(message);
        console.error('[Dashboard]', message);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  const occupancyRate = stats.total_slots > 0
    ? Math.round((stats.occupied_slots / stats.total_slots) * 100)
    : 0;

  const filteredSlots = slots.filter(slot => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      slot.slot_id.toLowerCase().includes(q) ||
      slot.status.toLowerCase().includes(q) ||
      slot.cluster?.toLowerCase().includes(q) ||
      slot.vehicle_plat?.toLowerCase().includes(q)
    );
  });

  const filteredEvents = events.filter(event => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      event.plat?.toLowerCase().includes(q) ||
      event.event_type.toLowerCase().includes(q) ||
      event.slot_id?.toLowerCase().includes(q) ||
      event.reason?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header
          title="Dashboard"
          subtitle="Real-time parking monitoring overview"
          connectionStatus={connectionStatus}
          onSearch={setSearchQuery}
        />
        <main className="flex-1 overflow-y-auto p-6">
          {error && (
            <div className="mb-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 text-sm">
              Error: {error}
            </div>
          )}
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatsCard title="Total Slots" value={stats.total_slots} icon={ParkingSquare} />
              <StatsCard title="Available" value={loading ? '...' : stats.available_slots} icon={ParkingSquare} />
              <StatsCard title="Occupancy Rate" value={loading ? '...' : `${occupancyRate}%`} icon={TrendingUp} />
              <StatsCard title="Events Today" value={loading ? '...' : stats.today_events} icon={AlertTriangle} />
            </div>
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <div className="lg:col-span-2">
                <div className="rounded-lg border border-border bg-card p-6">
                  <h2 className="mb-4 text-xl font-bold text-foreground">Parking Map</h2>
                  <ParkingGrid slots={filteredSlots} />
                </div>
              </div>
              <div className="lg:col-span-1">
                <div className="rounded-lg border border-border bg-card p-6">
                  <h2 className="mb-4 text-xl font-bold text-foreground">Recent Events</h2>
                  <EventList events={filteredEvents} maxItems={5} />
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
