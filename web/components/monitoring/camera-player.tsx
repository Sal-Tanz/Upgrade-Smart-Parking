"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import Hls from "hls.js";
import { CameraSource } from "@/lib/api/types";
import { cameraApi } from "@/lib/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Video,
  VideoOff,
  Maximize2,
  RefreshCw,
  Camera,
  ScanText,
  Settings,
  AlertCircle,
  CheckCircle2,
  ExternalLink,
} from "lucide-react";
import Link from "next/link";

interface CameraPlayerProps {
  cameras: CameraSource[];
  selectedCameraId?: number;
  onCameraChange?: (cameraId: number) => void;
  showCameraSelector?: boolean;
  className?: string;
  onPlateDetected?: (plateData: any) => void;
}

export function CameraPlayer({
  cameras,
  selectedCameraId,
  onCameraChange,
  showCameraSelector = true,
  className = "",
  onPlateDetected,
}: CameraPlayerProps) {
  const [activeId, setActiveId] = useState<number | null>(
    selectedCameraId || (cameras.length > 0 ? cameras[0].id : null)
  );
  const [mode, setMode] = useState<"auto" | "hls" | "proxy">("auto");
  const [status, setStatus] = useState<"connecting" | "live" | "offline" | "error">("connecting");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [detecting, setDetecting] = useState(false);
  const [detectionResult, setDetectionResult] = useState<any>(null);
  const [snapshotLoading, setSnapshotLoading] = useState(false);
  const [streamKey, setStreamKey] = useState(Date.now());

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const hlsRef = useRef<Hls | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Synchronize internal active camera when prop changes
  useEffect(() => {
    if (selectedCameraId && selectedCameraId !== activeId) {
      setActiveId(selectedCameraId);
    } else if (!activeId && cameras.length > 0) {
      setActiveId(cameras[0].id);
    }
  }, [selectedCameraId, cameras, activeId]);

  const currentCamera = cameras.find((c) => c.id === activeId) || cameras[0] || null;
  const isM3u8 = currentCamera
    ? (currentCamera.resolved_stream_type || currentCamera.stream_type) === "m3u8" ||
      currentCamera.url.toLowerCase().includes(".m3u8")
    : false;

  const shouldUseHls = currentCamera && isM3u8 && mode !== "proxy";

  // Initialize or teardown HLS player
  useEffect(() => {
    if (!currentCamera) {
      setStatus("offline");
      return;
    }

    setStatus("connecting");
    setErrorMessage(null);

    // Clean up previous HLS instance
    if (hlsRef.current) {
      hlsRef.current.destroy();
      hlsRef.current = null;
    }

    if (!shouldUseHls) {
      // For RTSP / proxy mode, stream is handled by <img> MJPEG element
      return;
    }

    const video = videoRef.current;
    if (!video) return;

    const streamUrl = currentCamera.url.toLowerCase().startsWith("rstp://")
      ? "rtsp://" + currentCamera.url.slice(7)
      : currentCamera.url;

    let networkErrorRetries = 0;

    if (Hls.isSupported()) {
      const hls = new Hls({
        enableWorker: true,
        lowLatencyMode: true,
        backBufferLength: 60,
      });
      hlsRef.current = hls;

      hls.loadSource(streamUrl);
      hls.attachMedia(video);

      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        setStatus("live");
        video.play().catch(() => {
          // Autoplay policy might block unmuted playback
          video.muted = true;
          video.play().catch(() => {});
        });
      });

      hls.on(Hls.Events.ERROR, (_event, data) => {
        if (data.fatal) {
          switch (data.type) {
            case Hls.ErrorTypes.NETWORK_ERROR:
              networkErrorRetries += 1;
              if (networkErrorRetries <= 2) {
                setErrorMessage("Koneksi jaringan HLS terputus. Mencoba memulihkan...");
                hls.startLoad();
              } else {
                setStatus("error");
                setErrorMessage(
                  "Gagal memutar link stream m3u8 langsung di browser (CORS atau Server Offline). Silakan beralih ke Mode Proxy Backend."
                );
                hls.destroy();
              }
              break;
            case Hls.ErrorTypes.MEDIA_ERROR:
              setErrorMessage("Error media HLS. Memulihkan stream...");
              hls.recoverMediaError();
              break;
            default:
              setStatus("error");
              setErrorMessage(
                "Gagal memutar link stream m3u8 langsung (CORS/Offline). Coba ganti ke Mode Proxy Backend."
              );
              hls.destroy();
              break;
          }
        }
      });
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      // Native HLS for Safari / iOS
      video.src = streamUrl;
      video.addEventListener("loadedmetadata", () => {
        setStatus("live");
        video.play().catch(() => {});
      });
      video.addEventListener("error", () => {
        setStatus("error");
        setErrorMessage("Gagal memuat stream video m3u8 di browser.");
      });
    } else {
      setStatus("error");
      setErrorMessage("Browser Anda tidak mendukung HLS. Beralih ke Mode Proxy Backend.");
    }

    return () => {
      if (hlsRef.current) {
        hlsRef.current.destroy();
        hlsRef.current = null;
      }
    };
  }, [currentCamera, shouldUseHls, streamKey]);

  const handleCameraSelect = (id: number) => {
    setActiveId(id);
    setDetectionResult(null);
    setErrorMessage(null);
    setStreamKey(Date.now());
    onCameraChange?.(id);
  };

  const handleRefresh = () => {
    setStreamKey(Date.now());
    setStatus("connecting");
  };

  const handleFullscreen = () => {
    if (!containerRef.current) return;
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  };

  const handleCaptureSnapshot = async () => {
    if (!currentCamera) return;
    try {
      setSnapshotLoading(true);
      const snapshotUrl = `${cameraApi.getSnapshotUrl(currentCamera.id)}?t=${Date.now()}`;
      const res = await fetch(snapshotUrl);
      if (!res.ok) {
        setErrorMessage("Gagal mengambil snapshot dari kamera (kamera offline)");
        return;
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `snapshot_${currentCamera.name.replace(/\s+/g, "_")}_${Date.now()}.jpg`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to capture snapshot:", err);
      setErrorMessage("Gagal mengunduh snapshot");
    } finally {

      setSnapshotLoading(false);
    }
  };

  const handleDetectPlate = async () => {
    if (!currentCamera) return;
    try {
      setDetecting(true);
      setDetectionResult(null);
      const res = await cameraApi.detect(currentCamera.id, true);
      if (res.success && res.data) {
        setDetectionResult(res.data);
        onPlateDetected?.(res.data);
      } else {
        setDetectionResult({
          error: res.error || "Gagal melakukan deteksi ALPR dari stream kamera",
        });
      }
    } catch (err) {
      setDetectionResult({
        error: err instanceof Error ? err.message : "Gagal memproses deteksi plat",
      });
    } finally {
      setDetecting(false);
    }
  };

  if (!currentCamera || cameras.length === 0) {
    return (
      <div
        className={`flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/60 p-8 text-center ${className}`}
      >
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-accent/10 text-accent mb-4">
          <VideoOff className="h-7 w-7" />
        </div>
        <h3 className="text-lg font-semibold text-foreground">Belum Ada Sumber Kamera</h3>
        <p className="mt-1 max-w-md text-sm text-muted-foreground">
          Tambahkan link stream RTSP atau m3u8 melalui menu pengaturan untuk memantau kendaraan di gate atau area parkir secara live.
        </p>
        <Link href="/settings" className="mt-4">
          <Button variant="default" className="gap-2">
            <Settings className="h-4 w-4" />
            Atur Sumber Kamera di Pengaturan
          </Button>
        </Link>
      </div>
    );
  }

  const streamType = currentCamera.resolved_stream_type || currentCamera.stream_type;
  const proxyStreamUrl = `${cameraApi.getStreamUrl(currentCamera.id)}?t=${streamKey}`;

  return (
    <div
      ref={containerRef}
      className={`relative flex flex-col overflow-hidden rounded-xl border border-border bg-card shadow-sm ${className}`}
    >
      {/* Top Header / Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border bg-muted/40 px-4 py-3">
        <div className="flex items-center gap-2">
          <Video className="h-5 w-5 text-accent" />
          {showCameraSelector && cameras.length > 1 ? (
            <select
              value={currentCamera.id}
              onChange={(e) => handleCameraSelect(Number(e.target.value))}
              className="rounded-md border border-border bg-background px-3 py-1.5 text-sm font-medium text-foreground focus:outline-none focus:ring-2 focus:ring-accent cursor-pointer"
            >
              {cameras.map((cam) => (
                <option key={cam.id} value={cam.id}>
                  {cam.name} {cam.location ? `(${cam.location})` : ""}
                </option>
              ))}
            </select>
          ) : (
            <div>
              <span className="font-semibold text-foreground">{currentCamera.name}</span>
              {currentCamera.location && (
                <span className="ml-2 text-xs text-muted-foreground">({currentCamera.location})</span>
              )}
            </div>
          )}

          {/* Stream Type Badge */}
          <Badge
            variant="outline"
            className={`uppercase text-xs font-bold ${
              streamType === "rtsp"
                ? "border-purple-500/30 bg-purple-500/10 text-purple-400"
                : streamType === "m3u8"
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                : "border-blue-500/30 bg-blue-500/10 text-blue-400"
            }`}
          >
            {streamType === "m3u8" ? "M3U8 / HLS" : streamType.toUpperCase()}
          </Badge>

          {/* Connection Status Badge */}
          <Badge
            variant={status === "live" ? "default" : status === "error" ? "destructive" : "secondary"}
            className="gap-1 text-xs"
          >
            <span
              className={`h-2 w-2 rounded-full ${
                status === "live"
                  ? "bg-status-available animate-pulse-available"
                  : status === "error"
                  ? "bg-status-occupied"
                  : "bg-status-reserved animate-pulse"
              }`}
            />
            {status === "live" ? "LIVE" : status === "error" ? "OFFLINE" : "CONNECTING"}
          </Badge>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-1.5">
          {/* Mode Switcher for M3U8 */}
          {isM3u8 && (
            <div className="flex items-center rounded-md border border-border bg-background p-0.5 text-xs">
              <button
                onClick={() => setMode("auto")}
                className={`rounded px-2 py-1 font-medium transition-colors ${
                  mode === "auto" ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:text-foreground"
                }`}
                title="HLS Player Langsung"
              >
                HLS
              </button>
              <button
                onClick={() => setMode("proxy")}
                className={`rounded px-2 py-1 font-medium transition-colors ${
                  mode === "proxy" ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:text-foreground"
                }`}
                title="Backend MJPEG Stream Proxy"
              >
                Proxy
              </button>
            </div>
          )}

          <Button
            size="sm"
            variant="outline"
            onClick={handleCaptureSnapshot}
            disabled={snapshotLoading}
            className="h-8 px-2.5 text-xs gap-1"
            title="Ambil snapshot gambar"
          >
            <Camera className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Snapshot</span>
          </Button>

          <Button
            size="sm"
            variant="default"
            onClick={handleDetectPlate}
            disabled={detecting}
            className="h-8 px-2.5 text-xs gap-1 bg-accent text-accent-foreground hover:bg-accent/90"
            title="Ambil frame dan jalankan deteksi ALPR"
          >
            <ScanText className={`h-3.5 w-3.5 ${detecting ? "animate-spin" : ""}`} />
            <span>{detecting ? "Mendeteksi..." : "Deteksi ALPR"}</span>
          </Button>

          <Button
            size="sm"
            variant="ghost"
            onClick={handleRefresh}
            className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
            title="Refresh stream"
          >
            <RefreshCw className="h-4 w-4" />
          </Button>

          <Button
            size="sm"
            variant="ghost"
            onClick={handleFullscreen}
            className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
            title="Layar penuh"
          >
            <Maximize2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Video Stream Display Area */}
      <div className="relative aspect-video w-full overflow-hidden bg-black flex items-center justify-center">
        {shouldUseHls ? (
          <video
            ref={videoRef}
            className="h-full w-full object-contain"
            autoPlay
            playsInline
            muted
            controls={false}
          />
        ) : status === "error" ? (
          <div className="flex flex-col items-center justify-center p-6 text-center text-muted-foreground">
            <VideoOff className="h-10 w-10 text-red-400/80 mb-2" />
            <p className="text-sm font-semibold text-foreground">Stream Tidak Tersedia</p>
            <p className="text-xs text-muted-foreground mt-1 max-w-xs">
              {errorMessage || "Kamera offline atau link stream tidak merespons"}
            </p>
            <div className="flex items-center gap-2 mt-3">
              <Button size="sm" variant="outline" onClick={handleRefresh} className="h-7 text-xs gap-1">
                <RefreshCw className="h-3 w-3" />
                Coba Lagi
              </Button>
              {isM3u8 && mode !== "proxy" && (
                <Button size="sm" variant="default" onClick={() => setMode("proxy")} className="h-7 text-xs bg-accent text-accent-foreground">
                  Gunakan Proxy Backend
                </Button>
              )}
            </div>
          </div>
        ) : (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            key={proxyStreamUrl}
            src={proxyStreamUrl}
            alt={`Live stream ${currentCamera.name}`}
            className="h-full w-full object-contain"
            onLoad={() => setStatus("live")}
            onError={() => {
              setStatus("error");
              setErrorMessage("Kamera tidak dapat dihubungi atau stream terputus.");
            }}
          />
        )}


        {/* Live Indicator Overlay */}
        <div className="absolute top-3 left-3 flex items-center gap-2 rounded-md bg-black/60 backdrop-blur-md px-2.5 py-1 text-xs text-white">
          <span className="h-2 w-2 rounded-full bg-red-500 animate-ping" />
          <span className="font-semibold uppercase tracking-wider text-[11px]">REC / LIVE</span>
        </div>

        {/* Stream Source URL Overlay (Watermark) */}
        <div className="absolute bottom-3 left-3 rounded bg-black/60 px-2 py-0.5 text-[11px] text-gray-300 font-mono max-w-[80%] truncate">
          {currentCamera.name} • {currentCamera.location || "Gate"}
        </div>

        {/* Error / Offline Alert Banner */}
        {errorMessage && (
          <div className="absolute top-12 left-4 right-4 z-20 flex items-center justify-between rounded-lg border border-amber-500/30 bg-amber-950/80 p-3 text-xs text-amber-200 backdrop-blur-sm">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0 text-amber-400" />
              <span>{errorMessage}</span>
            </div>
            {isM3u8 && mode !== "proxy" && (
              <button
                onClick={() => setMode("proxy")}
                className="ml-3 shrink-0 rounded bg-amber-500/20 px-2 py-1 font-semibold text-amber-300 hover:bg-amber-500/30"
              >
                Gunakan Proxy Backend
              </button>
            )}
          </div>
        )}
      </div>

      {/* Detection Result Drawer / Banner */}
      {detectionResult && (
        <div className="border-t border-border bg-card p-4 transition-all animate-in fade-in">
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold uppercase text-muted-foreground">
                  Hasil Deteksi ALPR Real-time
                </span>
                {detectionResult.error ? (
                  <Badge variant="destructive" className="text-xs">
                    Gagal
                  </Badge>
                ) : (
                  <Badge
                    variant={detectionResult.validation?.status === "ACCEPTED" ? "default" : "destructive"}
                    className="text-xs"
                  >
                    {detectionResult.validation?.status || "TERDETEKSI"}
                  </Badge>
                )}
              </div>

              {detectionResult.error ? (
                <p className="text-sm text-red-400">{detectionResult.error}</p>
              ) : (
                <div className="flex flex-wrap items-baseline gap-3 pt-1">
                  <span className="font-mono text-xl font-bold tracking-wider text-foreground">
                    {detectionResult.detection?.plate_text || "Plat Tidak Terbaca"}
                  </span>
                  {detectionResult.detection?.overall_confidence && (
                    <span className="text-xs text-muted-foreground">
                      Confidence: {(detectionResult.detection.overall_confidence * 100).toFixed(1)}%
                    </span>
                  )}
                  {detectionResult.validation?.nama_pemilik && (
                    <span className="text-xs text-muted-foreground">
                      Pemilik: <strong className="text-foreground">{detectionResult.validation.nama_pemilik}</strong>
                    </span>
                  )}
                  {detectionResult.validation?.cluster && (
                    <span className="text-xs text-muted-foreground">
                      Cluster: <strong className="text-accent">{detectionResult.validation.cluster}</strong>
                    </span>
                  )}
                  {detectionResult.validation?.buzzer_pattern && (
                    <span className="text-xs text-muted-foreground">
                      Buzzer: <strong className="font-mono">{detectionResult.validation.buzzer_pattern}</strong>
                    </span>
                  )}
                </div>
              )}
            </div>

            <button
              onClick={() => setDetectionResult(null)}
              className="text-xs text-muted-foreground hover:text-foreground p-1"
            >
              ✕ Tutup
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
