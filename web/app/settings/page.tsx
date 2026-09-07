"use client";

import { useState } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { CameraSettings } from "@/components/monitoring/camera-settings";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Video, Sliders, Bell, Cpu, ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<"cameras" | "alpr" | "system">("cameras");

  // System parameters mock state for ALPR / MQTT
  const [ocrConfidence, setOcrConfidence] = useState("0.80");
  const [detectionConfidence, setDetectionConfidence] = useState("0.25");
  const [gateDuration, setGateDuration] = useState("120");
  const [mqttBroker, setMqttBroker] = useState("localhost:1883");
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleSaveSystemSettings = (e: React.FormEvent) => {
    e.preventDefault();
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header
          title="Pengaturan Sistem & Monitoring"
          subtitle="Konfigurasi sumber kamera RTSP/M3U8, parameter ALPR, dan perangkat keras"
        />

        <main className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Navigation link back to Dashboard */}
          <div className="flex items-center justify-between">
            <Link href="/">
              <Button variant="ghost" size="sm" className="gap-2 text-muted-foreground hover:text-foreground">
                <ArrowLeft className="h-4 w-4" />
                Kembali ke Dashboard Monitoring
              </Button>
            </Link>

            {/* Tab Switcher */}
            <div className="flex items-center rounded-lg border border-border bg-muted/40 p-1">
              <button
                onClick={() => setActiveTab("cameras")}
                className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
                  activeTab === "cameras"
                    ? "bg-accent text-accent-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Video className="h-4 w-4" />
                Sumber Kamera (RTSP & M3U8)
              </button>
              <button
                onClick={() => setActiveTab("alpr")}
                className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
                  activeTab === "alpr"
                    ? "bg-accent text-accent-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Sliders className="h-4 w-4" />
                Parameter ALPR & Gate
              </button>
              <button
                onClick={() => setActiveTab("system")}
                className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
                  activeTab === "system"
                    ? "bg-accent text-accent-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Cpu className="h-4 w-4" />
                MQTT & Jaringan
              </button>
            </div>
          </div>

          {/* Tab 1: Camera Sources Configuration (Authoritative Task Feature) */}
          {activeTab === "cameras" && <CameraSettings />}

          {/* Tab 2: ALPR & Gate Parameters */}
          {activeTab === "alpr" && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base font-semibold">Parameter Deteksi ALPR & Kontrol Gate</CardTitle>
                <CardDescription>
                  Atur ambang batas keyakinan deteksi plat nomor dan durasi pembukaan gate otomatis.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSaveSystemSettings} className="space-y-4 max-w-xl">
                  {saveSuccess && (
                    <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 px-4 py-2 text-xs">
                      Pengaturan ALPR berhasil disimpan!
                    </div>
                  )}
                  <div className="space-y-1.5">
                    <Label htmlFor="det-conf">Detection Confidence Threshold (YOLO)</Label>
                    <Input
                      id="det-conf"
                      value={detectionConfidence}
                      onChange={(e) => setDetectionConfidence(e.target.value)}
                      placeholder="0.25"
                    />
                    <p className="text-[11px] text-muted-foreground">
                      Nilai ambang deteksi bounding box plat nomor (0.1 - 0.9). Default: 0.25
                    </p>
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="ocr-conf">OCR Confidence Minimum</Label>
                    <Input
                      id="ocr-conf"
                      value={ocrConfidence}
                      onChange={(e) => setOcrConfidence(e.target.value)}
                      placeholder="0.80"
                    />
                    <p className="text-[11px] text-muted-foreground">
                      Ambang batas kepercayaan pembacaan karakter plat oleh PaddleOCR. Default: 0.80
                    </p>
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="gate-dur">Durasi Palang Terbuka (Detik)</Label>
                    <Input
                      id="gate-dur"
                      value={gateDuration}
                      onChange={(e) => setGateDuration(e.target.value)}
                      placeholder="120"
                    />
                    <p className="text-[11px] text-muted-foreground">
                      Waktu tunggu palang gerbang sebelum menutup otomatis jika tidak ada kendaraan.
                    </p>
                  </div>

                  <Button type="submit" className="bg-accent text-accent-foreground">
                    Simpan Parameter ALPR
                  </Button>
                </form>
              </CardContent>
            </Card>
          )}

          {/* Tab 3: System & MQTT */}
          {activeTab === "system" && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base font-semibold">Integrasi Broker MQTT & Notifikasi</CardTitle>
                <CardDescription>
                  Konfigurasi komunikasi IoT dengan perangkat palang pintu, buzzer, dan sensor RFID.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSaveSystemSettings} className="space-y-4 max-w-xl">
                  <div className="space-y-1.5">
                    <Label htmlFor="mqtt-broker">Alamat MQTT Broker</Label>
                    <Input
                      id="mqtt-broker"
                      value={mqttBroker}
                      onChange={(e) => setMqttBroker(e.target.value)}
                      placeholder="localhost:1883"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="mqtt-topic-gate">Topic Gate Masuk</Label>
                    <Input id="mqtt-topic-gate" defaultValue="parking/gate/entry" />
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="mqtt-topic-buzzer">Topic Buzzer Pelanggaran</Label>
                    <Input id="mqtt-topic-buzzer" defaultValue="parking/buzzer/alarm" />
                  </div>

                  <Button type="submit" className="bg-accent text-accent-foreground">
                    Simpan Konfigurasi MQTT
                  </Button>
                </form>
              </CardContent>
            </Card>
          )}
        </main>
      </div>
    </div>
  );
}