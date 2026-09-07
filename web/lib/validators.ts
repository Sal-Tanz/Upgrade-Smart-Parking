import { z } from "zod";

// Login form validation
export const loginSchema = z.object({
  username: z
    .string()
    .min(3, "Username minimal 3 karakter")
    .max(50, "Username maksimal 50 karakter"),
  password: z
    .string()
    .min(6, "Password minimal 6 karakter")
    .max(100, "Password maksimal 100 karakter"),
});

export type LoginFormData = z.infer<typeof loginSchema>;

// Vehicle form validation
export const vehicleSchema = z.object({
  plat: z
    .string()
    .min(1, "Plat nomor wajib diisi")
    .max(20, "Plat nomor maksimal 20 karakter")
    .regex(/^[A-Za-z]{1,2}\s?\d{1,4}\s?[A-Za-z]{0,3}$/, "Format plat tidak valid (contoh: B 1234 XYZ)"),
  owner: z
    .string()
    .min(1, "Nama pemilik wajib diisi")
    .max(100, "Nama pemilik maksimal 100 karakter"),
  role: z
    .enum(["D", "W", "S"], {
      message: "Pilih jabatan yang valid (D/W/S)",
    }),
  status: z.enum(["active", "inactive"], {
    message: "Pilih status yang valid",
  }),
});

export type VehicleFormData = z.infer<typeof vehicleSchema>;

// Event filter validation
export const eventFilterSchema = z.object({
  eventType: z.string().optional(),
  plateNumber: z.string().optional(),
  cluster: z.string().optional(),
  status: z.string().optional(),
  dateFrom: z.string().optional(),
  dateTo: z.string().optional(),
});

export type EventFilterData = z.infer<typeof eventFilterSchema>;

// Attendance filter validation
export const attendanceFilterSchema = z.object({
  dateFrom: z.string().optional(),
  dateTo: z.string().optional(),
  status: z.string().optional(),
});

export type AttendanceFilterData = z.infer<typeof attendanceFilterSchema>;

// Pagination validation
export const paginationSchema = z.object({
  page: z.number().int().min(1).default(1),
  limit: z.number().int().min(1).max(100).default(10),
});

export type PaginationData = z.infer<typeof paginationSchema>;
