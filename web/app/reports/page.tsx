"use client";

import { useEffect, useState } from "react";
import { attendanceApi } from "@/lib/api/client";
import type { AttendanceRecord } from "@/lib/api/types";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { format } from "date-fns";
import { TrendingUp, Clock, CheckCircle, Calendar } from "lucide-react";
import { DashboardShell } from "@/components/layout/dashboard-shell";

export default function ReportsPage() {
  const [records, setRecords] = useState<AttendanceRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  useEffect(() => {
    fetchRecords();
  }, [dateFrom, dateTo]);

  async function fetchRecords() {
    try {
      setLoading(true);
      setError(null);
      const response = await attendanceApi.getAll({
        limit: 1000,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined
      });
      if (response.success && response.data) {
        setRecords(response.data);
      } else {
        setError("Failed to load attendance records");
      }
    } catch (err) {
      setError("Error loading attendance records");
    } finally {
      setLoading(false);
    }
  }

  // Calculate statistics
  const totalRecords = records.length;
  const onTimeRecords = records.filter(
    (r) => r.arrival_status === "TEPAT_WAKTU" || r.status === "completed" || r.departure_status === "TEPAT_WAKTU"
  ).length;
  const onTimeRate = totalRecords > 0 ? ((onTimeRecords / totalRecords) * 100).toFixed(1) : "0.0";
  const totalDuration = records.reduce(
    (sum, r) => sum + (r.duration_minutes || r.parking_duration_minutes || 0),
    0
  );
  const avgDuration = totalRecords > 0 ? Math.round(totalDuration / totalRecords) : 0;

  // Group records by date for trend analysis
  const recordsByDate = records.reduce((acc, record) => {
    const entryDate = record.entry_time || record.arrival_time;
    let date = record.date;
    if (!date && entryDate) {
      try {
        date = format(new Date(entryDate), "yyyy-MM-dd");
      } catch {
        date = "Unknown";
      }
    }
    date = date || "Unknown";
    if (!acc[date]) {
      acc[date] = { total: 0, onTime: 0 };
    }
    acc[date].total++;
    const isCompleted =
      record.status === "completed" ||
      record.arrival_status === "TEPAT_WAKTU" ||
      record.departure_status === "TEPAT_WAKTU";
    if (isCompleted) {
      acc[date].onTime++;
    }
    return acc;
  }, {} as Record<string, { total: number; onTime: number }>);

  const sortedDates = Object.keys(recordsByDate).sort((a, b) => b.localeCompare(a)).slice(0, 14);

  function exportToCSV() {
    const headers = ["Plate Number", "Entry Time", "Exit Time", "Duration (min)", "Slot", "Status"];
    const rows = records.map(r => [
      r.plate_number,
      r.entry_time,
      r.exit_time || "",
      r.duration_minutes || "",
      r.slot_id || "",
      r.status
    ]);

    const csv = [headers, ...rows].map(row => row.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `attendance-report-${format(new Date(), "yyyy-MM-dd")}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (loading) {
    return (
      <DashboardShell title="Attendance Reports" subtitle="Analyze attendance patterns and trends">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent mx-auto"></div>
            <p className="mt-4 text-muted-foreground">Loading reports...</p>
          </div>
        </div>
      </DashboardShell>
    );
  }

  if (error) {
    return (
      <DashboardShell title="Attendance Reports" subtitle="Analyze attendance patterns and trends">
        <Card className="p-6 bg-red-500/10 border-red-500/30">
          <p className="text-red-400">{error}</p>
          <Button onClick={fetchRecords} className="mt-4" variant="outline">
            Retry
          </Button>
        </Card>
      </DashboardShell>
    );
  }

  return (
    <DashboardShell
      title="Attendance Reports"
      subtitle="Analyze attendance patterns and trends"
    >
      <div className="space-y-6">
        <div className="flex items-center justify-end">
          <Button onClick={exportToCSV} variant="outline">
            Export CSV
          </Button>
        </div>

      {/* Filters */}
      <Card className="p-4">
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <label className="text-sm font-medium text-foreground mb-2 block">Date From</label>
            <Input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
            />
          </div>
          <div className="flex-1">
            <label className="text-sm font-medium text-foreground mb-2 block">Date To</label>
            <Input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
            />
          </div>
          <div className="pt-6">
            <Button
              onClick={() => { setDateFrom(""); setDateTo(""); }}
              variant="ghost"
            >
              Clear
            </Button>
          </div>
        </div>
      </Card>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-accent/10 rounded-lg">
              <Calendar className="h-5 w-5 text-accent" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Total Records</p>
              <p className="text-2xl font-bold text-foreground">{totalRecords}</p>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-500/10 rounded-lg">
              <CheckCircle className="h-5 w-5 text-green-500" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">On-Time Rate</p>
              <p className="text-2xl font-bold text-foreground">{onTimeRate}%</p>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/10 rounded-lg">
              <Clock className="h-5 w-5 text-blue-500" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Avg Duration</p>
              <p className="text-2xl font-bold text-foreground">{avgDuration} min</p>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-500/10 rounded-lg">
              <TrendingUp className="h-5 w-5 text-purple-500" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Days Tracked</p>
              <p className="text-2xl font-bold text-foreground">{sortedDates.length}</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Trend Chart */}
      <Card className="p-6">
        <h2 className="text-lg font-semibold text-foreground mb-4">Attendance Trends (Last 14 Days)</h2>
        <div className="space-y-3">
          {sortedDates.length === 0 ? (
            <p className="text-center text-muted-foreground py-8">No data available for selected date range</p>
          ) : (
            sortedDates.map(date => {
              const data = recordsByDate[date];
              const onTimePercent = (data.onTime / data.total) * 100;
              return (
                <div key={date} className="flex items-center gap-3">
                  <div className="w-24 text-sm text-muted-foreground">
                    {(() => {
                      try {
                        return format(new Date(date), "MMM dd");
                      } catch {
                        return date;
                      }
                    })()}
                  </div>
                  <div className="flex-1 bg-muted rounded-full h-8 overflow-hidden">
                    <div
                      className="bg-green-500 h-full flex items-center justify-end pr-2 transition-all"
                      style={{ width: `${onTimePercent}%` }}
                    >
                      <span className="text-xs font-medium text-white">
                        {data.onTime}/{data.total}
                      </span>
                    </div>
                  </div>
                  <div className="w-16 text-sm text-right text-muted-foreground">
                    {onTimePercent.toFixed(0)}%
                  </div>
                </div>
              );
            })
          )}
        </div>
      </Card>

      {/* Recent Records Table */}
      <Card className="p-6">
        <h2 className="text-lg font-semibold text-foreground mb-4">Recent Records</h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Plate</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Entry</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Exit</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Duration</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Slot</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {records.slice(0, 20).map(record => {
                const entryDate = record.entry_time || record.arrival_time;
                const exitDate = record.exit_time || record.departure_time;
                return (
                  <tr key={record.id} className="hover:bg-muted/30">
                    <td className="px-4 py-3 text-sm font-mono text-foreground">
                      {record.plate_number || "-"}
                    </td>
                    <td className="px-4 py-3 text-sm text-foreground">
                      {entryDate ? format(new Date(entryDate), "MMM dd, HH:mm") : "-"}
                    </td>
                    <td className="px-4 py-3 text-sm text-foreground">
                      {exitDate ? format(new Date(exitDate), "MMM dd, HH:mm") : "-"}
                    </td>
                    <td className="px-4 py-3 text-sm text-foreground">
                      {record.duration_minutes ? `${record.duration_minutes} min` : "-"}
                    </td>
                  <td className="px-4 py-3 text-sm text-foreground">
                    {record.slot_id || "-"}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      record.status === "completed"
                        ? "bg-green-500/20 text-green-400"
                        : "bg-blue-500/20 text-blue-400"
                    }`}>
                      {record.status}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
          </table>
          {records.length > 20 && (
            <p className="text-center text-sm text-muted-foreground mt-4">
              Showing 20 of {records.length} records
            </p>
          )}
        </div>
      </Card>
    </div>
  </DashboardShell>
);
}

