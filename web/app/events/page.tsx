import { EventTable } from "@/components/events/event-table";

export default function EventsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Events</h1>
        <p className="text-muted-foreground">
          Monitor parking events and violations in real-time
        </p>
      </div>
      <EventTable />
    </div>
  );
}