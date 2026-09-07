import { EventTable } from "@/components/events/event-table";
import { DashboardShell } from "@/components/layout/dashboard-shell";

export default function EventsPage() {
  return (
    <DashboardShell
      title="Events"
      subtitle="Monitor parking events and violations in real-time"
    >
      <div className="space-y-6">
        <EventTable />
      </div>
    </DashboardShell>
  );
}