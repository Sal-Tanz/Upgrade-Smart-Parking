import { VehicleTable } from "@/components/vehicles/vehicle-table";

export default function VehiclesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Vehicles</h1>
        <p className="text-muted-foreground">
          Manage registered vehicles and their access permissions
        </p>
      </div>
      <VehicleTable />
    </div>
  );
}