/**
 * Event List Component
 *
 * Menampilkan daftar parking events dengan filter dan pagination
 */

import type { ParkingEvent } from '@/lib/api/types';
import { cn } from '@/lib/utils';

interface EventListProps {
  events: ParkingEvent[];
  maxItems?: number;
}

const eventTypeColors = {
  VALID: 'text-green-400',
  VIOLATION: 'text-red-400',
  REJECTED: 'text-orange-400',
  ACCEPTED: 'text-blue-400',
};

export function EventList({ events, maxItems = 50 }: EventListProps) {
  const displayEvents = events.slice(0, maxItems);

  return (
    <div className="space-y-3">
      {displayEvents.length === 0 ? (
        <div className="text-center text-muted-foreground py-8">
          No events found
        </div>
      ) : (
        displayEvents.map((event) => (
          <div
            key={event.id}
            className="rounded-lg border border-border bg-card p-4 hover:border-accent/50 transition-colors"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className={cn(
                      'text-sm font-semibold uppercase',
                      eventTypeColors[event.event_type as keyof typeof eventTypeColors] || 'text-foreground'
                    )}
                  >
                    {event.event_type}
                  </span>
                  {event.slot_id && (
                    <span className="text-xs text-muted-foreground">
                      • Slot {event.slot_id}
                    </span>
                  )}
                </div>

                <div className="text-sm text-foreground mb-1">
                  {(event.plat || event.plate_number) && (
                    <span className="font-mono font-semibold">{event.plat || event.plate_number}</span>
                  )}
                  {event.jabatan && (
                    <span className="ml-2 text-muted-foreground">
                      ({event.jabatan})
                    </span>
                  )}
                </div>

                <div className="text-xs text-muted-foreground">{event.reason || event.validation_result}</div>

                {(event.expected_cluster || event.actual_cluster) && (
                  <div className="mt-2 text-xs text-muted-foreground">
                    {event.expected_cluster && (
                      <span>Expected: {event.expected_cluster}</span>
                    )}
                    {event.actual_cluster && (
                      <span className="ml-3">Actual: {event.actual_cluster}</span>
                    )}
                  </div>
                )}
              </div>

              <div className="text-xs text-muted-foreground whitespace-nowrap">
                {(event.created_at || event.timestamp)
                  ? new Date(event.created_at || event.timestamp || "").toLocaleTimeString('id-ID', {
                      hour: '2-digit',
                      minute: '2-digit',
                    })
                  : '-'}
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
