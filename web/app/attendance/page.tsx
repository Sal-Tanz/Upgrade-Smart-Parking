import { AttendanceTable } from "@/components/attendance/attendance-table";
import { DashboardShell } from "@/components/layout/dashboard-shell";

export default function AttendancePage() {
  return (
    <DashboardShell
      title="Attendance"
      subtitle="View parking attendance records and duration"
    >
      <div className="space-y-6">
        <AttendanceTable />
      </div>
    </DashboardShell>
  );
}