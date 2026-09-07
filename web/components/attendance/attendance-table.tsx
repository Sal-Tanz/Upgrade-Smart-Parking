"use client";

import { useEffect, useState } from "react";
import { attendanceApi } from "@/lib/api/client";
import type { AttendanceRecord } from "@/lib/api/types";
import { Input } from "@/components/ui/input";
import { format } from "date-fns";

export function AttendanceTable() {
  const [records, setRecords] = useState<AttendanceRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    fetchRecords();
  }, []);

  async function fetchRecords() {
    try {
      setLoading(true);
      setError(null);
      const response = await attendanceApi.getAll({ limit: 100 });
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

  const filteredRecords = records.filter((record) => {
    const plateStr = (record.plate_number || record.plate || "").toLowerCase();
    const query = (searchTerm || "").toLowerCase();
    return plateStr.includes(query);
  });

  if (loading) {
    return <div className="p-6">Loading attendance records...</div>;
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
      <Input
        placeholder="Search by plate..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        className="max-w-sm"
      />

      <div className="rounded-md border">
        <table className="w-full">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium">Plate</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Entry Time</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Exit Time</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Duration</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Slot</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {filteredRecords.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">
                  No records found
                </td>
              </tr>
            ) : (
              filteredRecords.map((record) => {
                const entryDate = record.entry_time || record.arrival_time;
                const exitDate = record.exit_time || record.departure_time;
                return (
                  <tr key={record.id} className="hover:bg-muted/50">
                    <td className="px-4 py-3 font-mono text-sm">
                      {record.plate_number || record.plate || "-"}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {entryDate ? format(new Date(entryDate), "dd/MM/yyyy HH:mm") : "-"}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {exitDate ? format(new Date(exitDate), "dd/MM/yyyy HH:mm") : "-"}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {record.duration_minutes
                        ? `${record.duration_minutes} min`
                        : "-"}
                    </td>
                    <td className="px-4 py-3 text-sm">{record.slot_id || "-"}</td>
                    <td className="px-4 py-3 text-sm">
                      <span
                        className={`rounded-full px-2 py-1 text-xs ${
                          record.status === "completed"
                            ? "bg-green-500/20 text-green-400"
                            : "bg-blue-500/20 text-blue-400"
                        }`}
                      >
                        {record.status || "active"}
                      </span>
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