import { VehicleTable } from "@/components/vehicles/vehicle-table";
import { DashboardShell } from "@/components/layout/dashboard-shell";

export default function VehiclesPage() {
  return (
    <DashboardShell
      title="Vehicles"
      subtitle="Manage registered vehicles and their access permissions"
    >
      <div className="space-y-6">
        <VehicleTable />
      </div>
    </DashboardShell>
  );
}