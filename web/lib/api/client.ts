const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL !== undefined
  ? process.env.NEXT_PUBLIC_API_URL
  : (typeof window !== "undefined" ? "" : "http://localhost:8000");

interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

function getAuthHeaders(includeJsonContentType = true): HeadersInit {
  const headers: HeadersInit = includeJsonContentType ? { "Content-Type": "application/json" } : {};

  if (typeof window !== "undefined") {
    const token = localStorage.getItem("auth_token");
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  return headers;
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  try {
    const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
    const headers = await getAuthHeaders(!isFormData);
    const url = `${API_BASE_URL}${endpoint}`;

    const response = await fetch(url, {
      ...options,
      headers: {
        ...headers,
        ...options.headers,
      },
    });

    const data = await response.json();

    if (!response.ok) {
      return {
        success: false,
        error: data.detail || data.error || "Request failed",
      };
    }

    return { success: true, data: data as T };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "Unknown error",
    };
  }
}

// Vehicle API
export const vehicleApi = {
  getAll: async () => {
    const response = await apiClient<{ vehicles?: any[]; total?: number } | any[]>("/api/vehicles");
    let rawVehicles: any[] = [];
    if (response.success && response.data) {
      if (Array.isArray(response.data)) {
        rawVehicles = response.data;
      } else if (Array.isArray((response.data as any).vehicles)) {
        rawVehicles = (response.data as any).vehicles;
      }
    }
    const vehicles = rawVehicles.map((v: any) => ({
      ...v,
      plat: v.plat || v.plate || "",
      plate: v.plat || v.plate || "",
      nama_pemilik: v.nama_pemilik || v.owner || "",
      owner: v.nama_pemilik || v.owner || "",
      jabatan: v.jabatan || v.role || "S",
      role: v.jabatan || v.role || "S",
      aktif: v.aktif ?? (v.status === "active" || v.status === "aktif"),
      status: v.status || (v.aktif ? "active" : "inactive"),
    }));
    return { ...response, data: vehicles };
  },
  getById: (plate: string) => apiClient<any>(`/api/vehicles/${encodeURIComponent(plate)}`),
  create: (data: any) => {
    const payload = {
      plat: (data.plat || data.plate || "").trim().toUpperCase(),
      nama_pemilik: data.nama_pemilik || data.owner || "",
      jabatan: data.jabatan || data.role || "S",
    };
    return apiClient<any>("/api/vehicles", { method: "POST", body: JSON.stringify(payload) });
  },
  update: (plate: string, data: any) => {
    const payload = {
      nama_pemilik: data.nama_pemilik || data.owner,
      jabatan: data.jabatan || data.role,
    };
    return apiClient<any>(`/api/vehicles/${encodeURIComponent(plate)}`, { method: "PUT", body: JSON.stringify(payload) });
  },
  delete: (plate: string) => apiClient<void>(`/api/vehicles/${encodeURIComponent(plate)}`, { method: "DELETE" }),
};

// Parking API
export const parkingApi = {
  getAll: async () => {
    const response = await apiClient<{ slots: any[]; total: number }>("/api/slots");
    const rawSlots = response.data?.slots || [];
    const slots = rawSlots.map((s: any) => {
      let normalizedStatus = s.status;
      if (s.status === "kosong") normalizedStatus = "available";
      else if (s.status === "terisi") normalizedStatus = "occupied";
      return {
        ...s,
        status: normalizedStatus,
      };
    });
    return { ...response, data: slots };
  },
  getById: (id: string) => apiClient<any>(`/api/slots/${encodeURIComponent(id)}`),
  updateSlot: (slotId: string, status: string) => {
    const params = new URLSearchParams({ status });
    return apiClient<any>(`/api/slots/${encodeURIComponent(slotId)}?${params.toString()}`, { method: "PUT" });
  },
  validate: (plateNumber: string) => {
    const params = new URLSearchParams({ plate_text: plateNumber });
    return apiClient<any>(`/api/validate-plate?${params.toString()}`, { method: "POST" });
  },
  validateParking: (plateNumber: string, slotId: string) => {
    const params = new URLSearchParams({ plate_text: plateNumber, slot_id: slotId });
    return apiClient<any>(`/api/validate-parking?${params.toString()}`, { method: "POST" });
  },
};

// Event API
export const eventApi = {
  getAll: async (filters?: any) => {
    const params = new URLSearchParams();
    if (filters?.event_type) params.append("event_type", filters.event_type);
    if (filters?.plate_number) params.append("plate_number", filters.plate_number);
    if (filters?.resolved !== undefined) params.append("resolved", String(filters.resolved));
    if (filters?.limit) params.append("limit", filters.limit.toString());
    if (filters?.offset) params.append("offset", filters.offset.toString());

    const queryString = params.toString();
    const response = await apiClient<{ events: any[]; total: number; unresolved_count: number }>(
      `/api/events${queryString ? `?${queryString}` : ""}`
    );
    const rawEvents = response.data?.events || [];
    const events = rawEvents.map((e: any) => ({
      ...e,
      plat: e.plat || e.plate_number || "",
      plate_number: e.plate_number || e.plat || "",
      reason: e.reason || e.validation_result || e.event_type || "",
      validation_result: e.validation_result || e.reason || "",
      created_at: e.created_at || e.timestamp || new Date().toISOString(),
      timestamp: e.timestamp || e.created_at || new Date().toISOString(),
    }));
    return { ...response, data: events };
  },
  getById: (id: string) => apiClient<any>(`/api/events/${encodeURIComponent(id)}`),
  resolve: (id: string) => apiClient<any>(`/api/events/${encodeURIComponent(id)}/resolve`, { method: "POST" }),
};

// Detection / ML API
export const detectionApi = {
  detect: (file: File, validate = false) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiClient<any>(`/api/detect?validate=${validate}`, { method: "POST", body: formData });
  },
  detectBatch: (files: File[], validate = false) => {
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    return apiClient<any>(`/api/detect/batch?validate=${validate}`, { method: "POST", body: formData });
  },
};

// Attendance API
export const attendanceApi = {
  getAll: async (filters?: any) => {
    const params = new URLSearchParams();
    const dateFrom = filters?.date_from || filters?.dateFrom;
    const dateTo = filters?.date_to || filters?.dateTo;
    if (dateFrom) params.append("start_date", dateFrom);
    if (dateTo) params.append("end_date", dateTo);
    if (filters?.vehicle_id) params.append("vehicle_id", filters.vehicle_id.toString());
    if (filters?.limit) params.append("limit", filters.limit.toString());

    const queryString = params.toString();
    const response = await apiClient<{ records: any[]; total: number }>(
      `/api/attendance${queryString ? `?${queryString}` : ""}`
    );
    const rawRecords = response.data?.records || [];
    const records = rawRecords.map((r: any) => {
      const entryTime = r.entry_time || r.arrival_time || "";
      const exitTime = r.exit_time || r.departure_time || "";
      return {
        ...r,
        plate_number: r.plate_number || r.plate || (r.vehicle_id ? `Vehicle #${r.vehicle_id}` : "-"),
        entry_time: entryTime,
        exit_time: exitTime,
        arrival_time: entryTime,
        departure_time: exitTime,
        duration_minutes: r.duration_minutes ?? r.parking_duration_minutes ?? 0,
        parking_duration_minutes: r.parking_duration_minutes ?? r.duration_minutes ?? 0,
        status: r.status || (exitTime ? "completed" : "active"),
      };
    });
    return { ...response, data: records };
  },
};

// Camera API
export const cameraApi = {
  getAll: async (filters?: { is_active?: boolean }) => {
    const params = new URLSearchParams();
    if (filters?.is_active !== undefined) {
      params.append("is_active", String(filters.is_active));
    }
    const queryString = params.toString();
    const response = await apiClient<{ cameras: any[]; total: number }>(
      `/api/cameras${queryString ? `?${queryString}` : ""}`
    );
    const cameras = response.data?.cameras || [];
    return { ...response, data: cameras };
  },
  getById: (id: number) => apiClient<any>(`/api/cameras/${id}`),
  create: (data: {
    name: string;
    url: string;
    stream_type?: string;
    location?: string;
    is_active?: boolean;
  }) => {
    return apiClient<any>("/api/cameras", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },
  update: (
    id: number,
    data: Partial<{
      name: string;
      url: string;
      stream_type?: string;
      location?: string;
      is_active?: boolean;
    }>
  ) => {
    return apiClient<any>(`/api/cameras/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },
  delete: (id: number) =>
    apiClient<{ message: string; id: number }>(`/api/cameras/${id}`, {
      method: "DELETE",
    }),
  test: (data: { url: string; stream_type?: string }) => {
    return apiClient<any>("/api/cameras/test", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },
  testById: (id: number) => {
    return apiClient<any>(`/api/cameras/${id}/test`, {
      method: "POST",
    });
  },
  detect: (id: number, validate = true) => {
    return apiClient<any>(`/api/cameras/${id}/detect?validate=${validate}`, {
      method: "POST",
    });
  },
  getStreamUrl: (id: number) => `${API_BASE_URL}/api/cameras/${id}/stream`,
  getSnapshotUrl: (id: number) => `${API_BASE_URL}/api/cameras/${id}/snapshot`,
};

