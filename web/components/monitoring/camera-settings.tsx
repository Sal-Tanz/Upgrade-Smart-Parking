"use client";

import { useEffect, useState } from "react";
import { CameraSource, CameraTestResult } from "@/lib/api/types";
import { cameraApi } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Video,
  Plus,
  Trash2,
  Edit2,
  CheckCircle2,
  XCircle,
  Play,
  RefreshCw,
  HelpCircle,
  Radio,
  ExternalLink,
  ShieldAlert,
} from "lucide-react";
import { CameraPlayer } from "./camera-player";

export function CameraSettings() {
  const [cameras, setCameras] = useState<CameraSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Dialog state
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingCamera, setEditingCamera] = useState<CameraSource | null>(null);
  const [dialogError, setDialogError] = useState<string | null>(null);

  // Form state
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [streamType, setStreamType] = useState("auto");
  const [location, setLocation] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [saving, setSaving] = useState(false);

  // Test connection state
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<CameraTestResult | null>(null);

  // Row test connection results by camera ID
  const [rowTestResults, setRowTestResults] = useState<Record<number, CameraTestResult>>({});
  const [testingId, setTestingId] = useState<number | null>(null);

  // Preview modal state
  const [previewCamera, setPreviewCamera] = useState<CameraSource | null>(null);

  const fetchCameras = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await cameraApi.getAll();
      if (res.success && res.data) {
        setCameras(res.data);
      } else {
        setError(res.error || "Gagal mengambil daftar kamera");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal memuat sumber kamera");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCameras();
  }, []);

  const openCreateDialog = () => {
    setEditingCamera(null);
    setName("");
    setUrl("");
    setStreamType("auto");
    setLocation("");
    setIsActive(true);
    setTestResult(null);
    setDialogError(null);
    setIsDialogOpen(true);
  };

  const openEditDialog = (cam: CameraSource) => {
    setEditingCamera(cam);
    setName(cam.name);
    setUrl(cam.url);
    setStreamType(cam.stream_type || "auto");
    setLocation(cam.location || "");
    setIsActive(cam.is_active);
    setTestResult(null);
    setDialogError(null);
    setIsDialogOpen(true);
  };


  const handleTestUrl = async () => {
    if (!url.trim()) {
      setTestResult({
        success: false,
        message: "Silakan masukkan URL stream terlebih dahulu",
        stream_type: "unknown",
      });
      return;
    }

    try {
      setTesting(true);
      setTestResult(null);
      const res = await cameraApi.test({ url: url.trim(), stream_type: streamType });
      if (res.success && res.data) {
        setTestResult(res.data);
      } else {
        setTestResult({
          success: false,
          message: res.error || "Gagal menghubungi sumber stream",
          stream_type: streamType,
        });
      }
    } catch (err) {
      setTestResult({
        success: false,
        message: err instanceof Error ? err.message : "Koneksi stream gagal diuji",
        stream_type: streamType,
      });
    } finally {
      setTesting(false);
    }
  };

  const handleTestRow = async (id: number) => {
    try {
      setTestingId(id);
      const res = await cameraApi.testById(id);
      if (res.success && res.data) {
        setRowTestResults((prev) => ({ ...prev, [id]: res.data! }));
      } else {
        setRowTestResults((prev) => ({
          ...prev,
          [id]: {
            success: false,
            message: res.error || "Kamera offline atau URL salah",
            stream_type: "unknown",
          },
        }));
      }
    } catch (err) {
      setRowTestResults((prev) => ({
        ...prev,
        [id]: {
          success: false,
          message: err instanceof Error ? err.message : "Gagal menguji koneksi",
          stream_type: "unknown",
        },
      }));
    } finally {
      setTestingId(null);
    }
  };

  const handleSaveCamera = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !url.trim()) return;

    setDialogError(null);

    // Normalize rstp:// typo to rtsp://
    let cleanUrl = url.trim();
    if (cleanUrl.toLowerCase().startsWith("rstp://")) {
      cleanUrl = "rtsp://" + cleanUrl.slice(7);
    } else if (cleanUrl.toLowerCase().startsWith("rstps://")) {
      cleanUrl = "rtsps://" + cleanUrl.slice(8);
    }

    try {
      setSaving(true);
      if (editingCamera) {
        // Update
        const res = await cameraApi.update(editingCamera.id, {
          name: name.trim(),
          url: cleanUrl,
          stream_type: streamType === "rstp" ? "rtsp" : streamType,
          location: location.trim() || undefined,
          is_active: isActive,
        });
        if (!res.success) {
          setDialogError(res.error || "Gagal memperbarui kamera");
          return;
        }
      } else {
        // Create
        const res = await cameraApi.create({
          name: name.trim(),
          url: cleanUrl,
          stream_type: streamType === "rstp" ? "rtsp" : streamType,
          location: location.trim() || undefined,
          is_active: isActive,
        });
        if (!res.success) {
          setDialogError(res.error || "Gagal menambahkan kamera");
          return;
        }
      }

      setIsDialogOpen(false);
      await fetchCameras();
    } catch (err) {
      setDialogError(err instanceof Error ? err.message : "Gagal menyimpan kamera");
    } finally {
      setSaving(false);
    }
  };


  const handleDeleteCamera = async (id: number) => {
    if (!confirm("Apakah Anda yakin ingin menghapus sumber kamera ini?")) return;

    try {
      const res = await cameraApi.delete(id);
      if (res.success) {
        setCameras((prev) => prev.filter((c) => c.id !== id));
      } else {
        setError(res.error || "Gagal menghapus kamera");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal menghapus kamera");
    }
  };

  const handleToggleActive = async (cam: CameraSource) => {
    try {
      const res = await cameraApi.update(cam.id, { is_active: !cam.is_active });
      if (res.success && res.data) {
        setCameras((prev) => prev.map((c) => (c.id === cam.id ? res.data : c)));
      }
    } catch (err) {
      console.error("Failed to toggle camera active status:", err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <Radio className="h-5 w-5 text-accent animate-pulse" />
            Pengaturan Sumber Kamera CCTV
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Konfigurasi link stream <strong>RTSP</strong> atau <strong>M3U8 (HLS)</strong> untuk live monitoring, capture frame, dan deteksi ALPR otomatis.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchCameras} disabled={loading} className="gap-1.5">
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Muat Ulang
          </Button>
          <Button variant="default" size="sm" onClick={openCreateDialog} className="gap-1.5 bg-accent text-accent-foreground hover:bg-accent/90">
            <Plus className="h-4 w-4" />
            Tambah Sumber Kamera
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-xs hover:underline">
            Tutup
          </button>
        </div>
      )}

      {/* Camera List */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base font-semibold">Daftar Kamera Monitoring ({cameras.length})</CardTitle>
          <CardDescription>
            Kamera yang aktif akan langsung muncul di panel monitoring dashboard utama.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="py-12 text-center text-sm text-muted-foreground">Memuat data kamera...</div>
          ) : cameras.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted text-muted-foreground mb-3">
                <Video className="h-6 w-6" />
              </div>
              <p className="font-medium text-foreground">Belum ada kamera yang ditambahkan</p>
              <p className="text-xs text-muted-foreground mt-1 max-w-sm">
                Tambahkan kamera CCTV IP gerbang dengan URL RTSP atau link streaming m3u8 untuk memulai pemantauan.
              </p>
              <Button size="sm" onClick={openCreateDialog} className="mt-4 gap-1.5 bg-accent text-accent-foreground">
                <Plus className="h-4 w-4" />
                Tambah Kamera Sekarang
              </Button>
            </div>
          ) : (
            <div className="divide-y divide-border">
              {cameras.map((cam) => {
                const type = cam.resolved_stream_type || cam.stream_type;
                const test = rowTestResults[cam.id];
                return (
                  <div
                    key={cam.id}
                    className="flex flex-col sm:flex-row sm:items-center justify-between py-4 gap-4 transition-colors hover:bg-muted/20 px-2 rounded-lg"
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent/10 text-accent mt-0.5">
                        <Video className="h-5 w-5" />
                      </div>
                      <div className="space-y-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-semibold text-foreground">{cam.name}</span>
                          <Badge
                            variant="outline"
                            className={`uppercase text-[10px] font-bold ${
                              type === "rtsp"
                                ? "border-purple-500/40 bg-purple-500/10 text-purple-400"
                                : type === "m3u8"
                                ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-400"
                                : "border-blue-500/40 bg-blue-500/10 text-blue-400"
                            }`}
                          >
                            {type === "m3u8" ? "M3U8 / HLS" : type.toUpperCase()}
                          </Badge>
                          <Badge
                            variant={cam.is_active ? "default" : "secondary"}
                            className="text-[10px] cursor-pointer"
                            onClick={() => handleToggleActive(cam)}
                            title="Klik untuk ubah status aktif"
                          >
                            {cam.is_active ? "Aktif" : "Nonaktif"}
                          </Badge>
                          {cam.location && (
                            <span className="text-xs text-muted-foreground">• {cam.location}</span>
                          )}
                        </div>
                        <p className="text-xs font-mono text-muted-foreground break-all max-w-xl">
                          {cam.url}
                        </p>
                        {test && (
                          <div
                            className={`text-xs flex items-center gap-1.5 pt-0.5 ${
                              test.success ? "text-emerald-400" : "text-red-400"
                            }`}
                          >
                            {test.success ? (
                              <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
                            ) : (
                              <XCircle className="h-3.5 w-3.5 shrink-0" />
                            )}
                            <span>{test.message}</span>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0 self-end sm:self-center">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleTestRow(cam.id)}
                        disabled={testingId === cam.id}
                        className="h-8 text-xs gap-1"
                        title="Uji koneksi stream kamera ini"
                      >
                        <Radio className={`h-3.5 w-3.5 ${testingId === cam.id ? "animate-ping" : ""}`} />
                        <span>{testingId === cam.id ? "Menguji..." : "Uji"}</span>
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setPreviewCamera(cam)}
                        className="h-8 text-xs gap-1"
                        title="Live preview stream"
                      >
                        <Play className="h-3.5 w-3.5" />
                        <span>Preview</span>
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => openEditDialog(cam)}
                        className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
                        title="Edit kamera"
                      >
                        <Edit2 className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDeleteCamera(cam.id)}
                        className="h-8 w-8 p-0 text-muted-foreground hover:text-red-400"
                        title="Hapus kamera"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Guide Card for RTSP & M3U8 */}
      <Card className="bg-muted/30 border-dashed">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <HelpCircle className="h-4 w-4 text-accent" />
            Panduan Format URL Stream Kamera
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs space-y-3 text-muted-foreground">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="rounded-lg border border-border bg-card p-3 space-y-1">
              <span className="font-semibold text-foreground flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-purple-400" />
                Stream RTSP / RSTP (Real-Time Streaming Protocol)
              </span>
              <p>Format standar untuk CCTV IP camera (input <code>rstp://</code> otomatis dinormalisasi ke <code>rtsp://</code>):</p>
              <code className="block rounded bg-background p-1.5 font-mono text-[11px] text-accent">
                rtsp://[username]:[password]@[ip]:[port]/[path]
              </code>
              <p className="text-[11px] text-muted">
                Contoh: <code>rtsp://admin:12345@192.168.1.100:554/ch0</code>
              </p>
            </div>


            <div className="rounded-lg border border-border bg-card p-3 space-y-1">
              <span className="font-semibold text-foreground flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
                Stream M3U8 (HTTP Live Streaming / HLS)
              </span>
              <p>Format playlist stream HTTP/HTTPS untuk streaming web:</p>
              <code className="block rounded bg-background p-1.5 font-mono text-[11px] text-emerald-400">
                http(s)://[domain-atau-ip]/[path]/playlist.m3u8
              </code>
              <p className="text-[11px] text-muted">
                Contoh: <code>https://live.parking.id/gate1/index.m3u8</code>
              </p>
            </div>
          </div>
          <p className="text-[11px] text-muted">
            Tip: Backend Smart Parking akan secara otomatis memproxy stream RTSP menjadi format MJPEG yang kompatibel di semua browser, dan link m3u8 dapat diputar langsung di browser via HLS player!
          </p>
        </CardContent>
      </Card>

      {/* Dialog Add / Edit Camera */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <form onSubmit={handleSaveCamera}>
            <DialogHeader>
              <DialogTitle>
                {editingCamera ? "Edit Sumber Kamera" : "Tambah Sumber Kamera Baru"}
              </DialogTitle>
              <DialogDescription>
                Masukkan nama dan link stream RTSP atau m3u8 untuk kamera monitoring.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              {dialogError && (
                <div className="rounded-md bg-red-500/10 border border-red-500/30 text-red-400 p-2.5 text-xs flex items-center justify-between">
                  <span>{dialogError}</span>
                  <button type="button" onClick={() => setDialogError(null)} className="text-[10px] underline ml-2">
                    Tutup
                  </button>
                </div>
              )}

              {/* Camera Name */}
              <div className="space-y-1.5">
                <Label htmlFor="cam-name">Nama Kamera *</Label>
                <Input
                  id="cam-name"
                  placeholder="e.g. CCTV Gerbang Masuk Utara"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>

              {/* Stream URL */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label htmlFor="cam-url">URL Stream (RTSP / M3U8 / HTTP) *</Label>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={handleTestUrl}
                    disabled={testing || !url.trim()}
                    className="h-6 px-2 text-xs gap-1 text-accent hover:text-accent"
                  >
                    <Radio className={`h-3 w-3 ${testing ? "animate-ping" : ""}`} />
                    {testing ? "Menguji..." : "Uji Koneksi"}
                  </Button>
                </div>
                <Input
                  id="cam-url"
                  placeholder="rtsp://admin:pass@192.168.1.100:554/live atau https://.../stream.m3u8"
                  value={url}
                  onChange={(e) => {
                    setUrl(e.target.value);
                    setTestResult(null);
                  }}
                  required
                  className="font-mono text-xs"
                />

                {url.toLowerCase().startsWith("rstp://") && (
                  <p className="text-[11px] text-amber-400">
                    💡 Tip: Skema &quot;rstp://&quot; otomatis disesuaikan menjadi &quot;rtsp://&quot;.
                  </p>
                )}

                {/* Test Result Message */}
                {testResult && (
                  <div
                    className={`rounded-md p-2 text-xs flex items-center gap-2 ${
                      testResult.success
                        ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"
                        : "bg-red-500/10 border border-red-500/30 text-red-400"
                    }`}
                  >
                    {testResult.success ? (
                      <CheckCircle2 className="h-4 w-4 shrink-0" />
                    ) : (
                      <XCircle className="h-4 w-4 shrink-0" />
                    )}
                    <div>
                      <p className="font-medium">{testResult.message}</p>
                      {testResult.success && testResult.width && testResult.height && (
                        <p className="text-[11px] text-muted-foreground">
                          Resolusi: {testResult.width}x{testResult.height} | FPS: {testResult.fps || "-"} | Tipe: {testResult.stream_type}
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Stream Type & Location */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="cam-type">Tipe Stream</Label>
                  <select
                    id="cam-type"
                    value={streamType}
                    onChange={(e) => setStreamType(e.target.value)}
                    className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-accent"
                  >
                    <option value="auto">Otomatis (Deteksi URL)</option>
                    <option value="rtsp">RTSP (rtsp:// atau rstp://)</option>
                    <option value="m3u8">M3U8 / HLS (.m3u8)</option>
                    <option value="http">HTTP / MJPEG</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="cam-loc">Lokasi / Area</Label>
                  <Input
                    id="cam-loc"
                    placeholder="e.g. Gerbang Masuk, Cluster Merah"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                  />
                </div>
              </div>


              {/* Active Toggle */}
              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="cam-active"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                  className="rounded border-border text-accent focus:ring-accent h-4 w-4 cursor-pointer"
                />
                <Label htmlFor="cam-active" className="cursor-pointer">
                  Aktifkan kamera ini untuk monitoring langsung
                </Label>
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsDialogOpen(false)}>
                Batal
              </Button>
              <Button type="submit" disabled={saving || !name.trim() || !url.trim()} className="bg-accent text-accent-foreground">
                {saving ? "Menyimpan..." : editingCamera ? "Simpan Perubahan" : "Tambahkan Kamera"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Live Preview Modal */}
      {previewCamera && (
        <Dialog open={!!previewCamera} onOpenChange={(open) => !open && setPreviewCamera(null)}>
          <DialogContent className="sm:max-w-3xl">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Video className="h-5 w-5 text-accent" />
                Live Preview: {previewCamera.name}
              </DialogTitle>
              <DialogDescription>
                Stream live dari <code>{previewCamera.url}</code>
              </DialogDescription>
            </DialogHeader>

            <div className="py-2">
              <CameraPlayer
                cameras={[previewCamera]}
                selectedCameraId={previewCamera.id}
                showCameraSelector={false}
              />
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setPreviewCamera(null)}>
                Tutup
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
