/**
 * Parking Grid Component
 *
 * Menampilkan grid parking slots yang dikelompokkan berdasarkan cluster
 */

import type { ParkingSlot } from '@/lib/api/types';
import { cn } from '@/lib/utils';

interface ParkingGridProps {
  slots: ParkingSlot[];
  onSlotClick?: (slot: ParkingSlot) => void;
}

const statusColors = {
  available: 'bg-green-500/20 border-green-500 text-green-400',
  occupied: 'bg-red-500/20 border-red-500 text-red-400',
  reserved: 'bg-yellow-500/20 border-yellow-500 text-yellow-400',
  unknown: 'bg-gray-500/20 border-gray-500 text-gray-400',
};

export function ParkingGrid({ slots, onSlotClick }: ParkingGridProps) {
  // Group slots by cluster
  const groupedSlots = slots.reduce((acc, slot) => {
    const cluster = slot.cluster || 'Unknown';
    if (!acc[cluster]) {
      acc[cluster] = [];
    }
    acc[cluster].push(slot);
    return acc;
  }, {} as Record<string, ParkingSlot[]>);

  return (
    <div className="space-y-6">
      {Object.entries(groupedSlots).map(([cluster, clusterSlots]) => (
        <div key={cluster}>
          <h3 className="mb-3 text-lg font-semibold text-foreground">
            Cluster {cluster}
            <span className="ml-2 text-sm font-normal text-muted-foreground">
              ({clusterSlots.length} slots)
            </span>
          </h3>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
            {clusterSlots.map((slot) => (
              <button
                key={slot.slot_id}
                onClick={() => onSlotClick?.(slot)}
                className={cn(
                  'flex flex-col items-center justify-center rounded-lg border-2 p-4 transition-all',
                  'hover:scale-105 hover:shadow-lg cursor-pointer',
                  statusColors[slot.status as keyof typeof statusColors] || statusColors.unknown
                )}
              >
                <div className="text-lg font-bold">{slot.slot_id}</div>
                <div className="text-xs capitalize">{slot.status}</div>
                {slot.vehicle_plat && (
                  <div className="mt-2 text-xs text-muted-foreground truncate max-w-full">
                    {slot.vehicle_plat}
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
