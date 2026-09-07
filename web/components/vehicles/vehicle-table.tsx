"use client";

import { useEffect, useState } from "react";
import { vehicleApi } from "@/lib/api/client";
import type { Vehicle } from "@/lib/api/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { vehicleSchema, VehicleFormData } from "@/lib/validators";

export function VehicleTable() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingVehicle, setEditingVehicle] = useState<Vehicle | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<VehicleFormData>({
    resolver: zodResolver(vehicleSchema),
  });

  useEffect(() => {
    fetchVehicles();
  }, []);

  async function fetchVehicles() {
    try {
      setLoading(true);
      setError(null);
      const response = await vehicleApi.getAll();
      if (response.success && response.data) {
        setVehicles(response.data.vehicles);
      } else {
        setError("Failed to load vehicles");
      }
    } catch (err) {
      setError("Error loading vehicles");
    } finally {
      setLoading(false);
    }
  }

  async function onSubmit(data: VehicleFormData) {
    try {
      if (editingVehicle) {
        const response = await vehicleApi.update(editingVehicle.plat, data);
        if (response.success) {
          setDialogOpen(false);
          reset();
          setEditingVehicle(null);
          fetchVehicles();
        }
      } else {
        const response = await vehicleApi.create(data);
        if (response.success) {
          setDialogOpen(false);
          reset();
          fetchVehicles();
        }
      }
    } catch (err) {
      console.error("Error saving vehicle:", err);
    }
  }

  async function handleDelete(plat: string) {
    if (!confirm("Are you sure you want to delete this vehicle?")) return;
    try {
      const response = await vehicleApi.delete(plat);
      if (response.success) {
        fetchVehicles();
      }
    } catch (err) {
      console.error("Error deleting vehicle:", err);
    }
  }

  function handleEdit(vehicle: Vehicle) {
    setEditingVehicle(vehicle);
    setValue("plat", vehicle.plat);
    setValue("owner", vehicle.owner);
    setValue("role", vehicle.role);
    setValue("status", vehicle.status);
    setDialogOpen(true);
  }

  function handleAdd() {
    setEditingVehicle(null);
    reset();
    setDialogOpen(true);
  }

  const filteredVehicles = vehicles.filter(
    (v) =>
      v.plat.toLowerCase().includes(searchTerm.toLowerCase()) ||
      v.owner.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return <div className="p-6">Loading vehicles...</div>;
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
      <div className="flex items-center justify-between gap-4">
        <Input
          placeholder="Search by plate or owner..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="max-w-sm"
        />
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={handleAdd}>
              <Plus className="mr-2 h-4 w-4" />
              Add Vehicle
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                {editingVehicle ? "Edit Vehicle" : "Add New Vehicle"}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="plat">Plate Number</Label>
                <Input
                  id="plat"
                  placeholder="B 1234 XYZ"
                  {...register("plat")}
                  disabled={!!editingVehicle}
                />
                {errors.plat && (
                  <p className="text-xs text-red-400">{errors.plat.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="owner">Owner Name</Label>
                <Input
                  id="owner"
                  placeholder="John Doe"
                  {...register("owner")}
                />
                {errors.owner && (
                  <p className="text-xs text-red-400">{errors.owner.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label>Role</Label>
                <Select
                  onValueChange={(value) => setValue("role", value as "D" | "W" | "S")}
                  defaultValue={editingVehicle?.role}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select role" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="D">Dekan (D)</SelectItem>
                    <SelectItem value="W">Wakil Dekan (W)</SelectItem>
                    <SelectItem value="S">Staff (S)</SelectItem>
                  </SelectContent>
                </Select>
                {errors.role && (
                  <p className="text-xs text-red-400">{errors.role.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label>Status</Label>
                <Select
                  onValueChange={(value) => setValue("status", value as "active" | "inactive")}
                  defaultValue={editingVehicle?.status || "active"}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="inactive">Inactive</SelectItem>
                  </SelectContent>
                </Select>
                {errors.status && (
                  <p className="text-xs text-red-400">{errors.status.message}</p>
                )}
              </div>

              <div className="flex justify-end gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setDialogOpen(false);
                    reset();
                    setEditingVehicle(null);
                  }}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting
                    ? "Saving..."
                    : editingVehicle
                    ? "Update"
                    : "Add Vehicle"}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="rounded-md border">
        <table className="w-full">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium">Plate</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Owner</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Role</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Status</th>
              <th className="px-4 py-3 text-left text-sm font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {filteredVehicles.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                  No vehicles found
                </td>
              </tr>
            ) : (
              filteredVehicles.map((vehicle) => (
                <tr key={vehicle.plat} className="hover:bg-muted/50">
                  <td className="px-4 py-3 font-mono text-sm">{vehicle.plat}</td>
                  <td className="px-4 py-3 text-sm">{vehicle.owner}</td>
                  <td className="px-4 py-3 text-sm">{vehicle.role}</td>
                  <td className="px-4 py-3 text-sm">
                    <span
                      className={`rounded-full px-2 py-1 text-xs ${
                        vehicle.status === "active"
                          ? "bg-green-500/20 text-green-400"
                          : "bg-red-500/20 text-red-400"
                      }`}
                    >
                      {vehicle.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleEdit(vehicle)}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(vehicle.plat)}
                        className="text-red-400 hover:text-red-300"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}