"use client";

import { useEffect, useState } from "react";
import { eventApi } from "@/lib/api/client";
import type { ParkingEvent } from "@/lib/api/types";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CheckCircle, XCircle, AlertTriangle } from "lucide-react";
import { format } from "date-fns";

export function EventTable() {
  const [events, setEvents] = useState<ParkingEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterType, setFilterType] = useState<string>("all");

  useEffect(() => {
    fetchEvents();
    // Refresh every 30 seconds
    const interval = setInterval(fetchEvents, 30000);
    return () => clearInterval(interval);
  }, []);

  async function fetchEvents() {
    try {
      setLoading(true);
      setError(null);
      const response = await eventApi.getAll({ limit: 50 });
      if (response.success && response.data) {
        setEvents(response.data);
      } else {
        setError("Failed to load events");
      }
    } catch (err) {
      setError("Error loading events");
    } finally {
      setLoading(false);
    }
  }

  async function handleResolve(id: number) {
    try {
      const response = await eventApi.resolve(String(id));
      if (response.success) {
        fetchEvents();
      }
    } catch (err) {
      console.error("Error resolving event:", err);
    }
  }

  const filteredEvents = events.filter((event) => {
    const plateStr = (event.plat || event.plate_number || "").toLowerCase();
    const slotStr = (event.slot_id || "").toLowerCase();
    const matchesSearch =
      plateStr.includes(searchTerm.toLowerCase()) ||
      slotStr.includes(searchTerm.toLowerCase());
    const matchesFilter = filterType === "all" || event.event_type === filterType;
    return matchesSearch && matchesFilter;
  });

  if (loading) {
    return <div className="p-6">Loading events...</div>;
  }

  if (error) {
    return (
      <div className="rounded-md bg-red-500/10 p-4 text-sm text-red-400">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <Input
          placeholder="Search by plate or slot..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="max-w-sm"
        />
        <div className="flex gap-2">
          <Button
            variant={filterType === "all" ? "default" : "outline"}
            size="sm"
            onClick={() => setFilterType("all")}
          >
            All
          </Button>
          <Button
            variant={filterType === "VALID" ? "default" : "outline"}
            size="sm"
            onClick={() => setFilterType("VALID")}
          >
            Valid
          </Button>
          <Button
            variant={filterType === "VIOLATION" ? "default" : "outline"}
            size="sm"
            onClick={() => setFilterType("VIOLATION")}
          >
            Violations
          </Button>
        </div>
      </div>

      <div className="rounded-md border">
        <table className="w-full">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium">Time</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Plate</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Type</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Slot</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Cluster</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Status</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {filteredEvents.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-muted-foreground">
                  No events found
                </td>
              </tr>
            ) : (
              filteredEvents.map((event) => {
                const eventTime = event.timestamp || event.created_at;
                return (
                  <tr key={event.id} className="hover:bg-muted/50">
                    <td className="px-4 py-3 text-sm">
                      {eventTime ? format(new Date(eventTime), "dd/MM/yyyy HH:mm") : "-"}
                    </td>
                    <td className="px-4 py-3 font-mono text-sm">
                      {event.plat || event.plate_number || "-"}
                    </td>
                    <td className="px-4 py-3 text-sm">
                    <Badge
                      variant={
                        event.event_type === "VALID"
                          ? "default"
                          : event.event_type === "VIOLATION"
                          ? "destructive"
                          : "secondary"
                      }
                    >
                      {event.event_type}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-sm">{event.slot_id || "-"}</td>
                  <td className="px-4 py-3 text-sm">
                    {event.actual_cluster || "-"}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <Badge
                      variant={event.resolved ? "outline" : "default"}
                      className={
                        event.resolved
                          ? "bg-green-500/20 text-green-400"
                          : "bg-yellow-500/20 text-yellow-400"
                      }
                    >
                      {event.resolved ? "Resolved" : "Pending"}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    {!event.resolved && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleResolve(event.id)}
                      >
                        <CheckCircle className="h-4 w-4" />
                      </Button>
                    )}
                  </td>
                </tr>
              );
            })
          )}
          </tbody>
        </table>
      </div>
    </div>
  );
}