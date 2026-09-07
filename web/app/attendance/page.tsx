import { AttendanceTable } from "@/components/attendance/attendance-table";

export default function AttendancePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Attendance</h1>
        <p className="text-muted-foreground">
          View parking attendance records and duration
        </p>
      </div>
      <AttendanceTable />
    </div>
  );
}