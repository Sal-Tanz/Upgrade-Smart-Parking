# Smart Parking System

Sistem manajemen parkir cerdas berbasis computer vision. Mendeteksi plat nomor kendaraan menggunakan YOLOv8 + PaddleOCR, mencocokkan dengan database terdaftar, dan mengontrol palang parkir secara otomatis untuk dual lane (kiri & kanan).

## Deskripsi

## Fitur Utama

1. **Deteksi Plat Nomor (ALPR)** — YOLOv8 mendeteksi bounding box plat pada frame dengan padding margin tepi yang aman.
2. **OCR Plat Nomor Dua Arah** — PaddleOCR / EasyOCR membaca teks plat nomor dengan koreksi semantik digit-ke-huruf (prefix/suffix) dan huruf-ke-digit (nomor polisi), serta normalisasi salah ketik `13 -> B`.
3. **Sumber Kamera Fleksibel (RTSP & M3U8)** — Mendukung kamera IP/CCTV lokal lewat protokol RTSP (termasuk toleransi `rstp://`) maupun streaming HLS (`.m3u8`) yang dapat diatur dinamis di Web UI.
4. **Matching Database & Validasi Cluster** — Teks plat nomor dicocokkan ke database dan divalidasi dengan logika akses cluster parkir Karnaugh Map.
5. **Gate Control Dual Lane** — Palang pintu otomatis terbuka jika plat terdaftar dengan isolasi tracking antrean kendaraan di tiap lajur.
6. **Biner Mandiri Standalone (All-in-One)** — Eksekutabel tunggal Go (`./smartparking`) yang meng-embed Web UI Next.js, FastAPI supervisor, dan model ML tanpa perlu konfigurasi terpisah.

---

## Penggunaan

### 1. Menjalankan via Biner Standalone (Paling Praktis)

Aplikasi telah dibundel menjadi biner executable mandiri `./smartparking` yang mengintegrasikan Web UI, Backend API, dan Gateway Reverse Proxy dalam satu file:

```bash
# Menjalankan server lengkap (Web UI + Backend Gateway di http://localhost:8090)
./smartparking run

# Opsi kustom port
./smartparking run --port 8090 --backend 8008

# Menjalankan gate detection langsung lewat biner
./smartparking gate --stream rtsp://admin:pass@192.168.1.100:554/live

# Cek versi biner dan bantuan perintah
./smartparking version
./smartparking --help
```

---

### 2. Menjalankan Backend API & Frontend Web UI Manual (Development Mode)

Jika ingin menjalankan secara terpisah untuk pengembangan:

```bash
# Menggunakan Bash script (Linux / macOS)
./start.sh

# ATAU menggunakan Python script (Cross-platform)
python run.py
```

Layanan akan aktif pada:
- **Web UI Dashboard & Monitoring**: `http://localhost:3000` (atau `http://localhost:8090` jika menggunakan biner)
- **Backend API Docs (Swagger)**: `http://localhost:8000/docs`

---

### 3. Pengaturan Sumber Kamera di Web UI

Anda dapat mengatur sumber kamera CCTV secara interaktif tanpa menyentuh kode:
1. Buka Web UI Monitoring, masuk ke menu **Pengaturan** (`/settings`).
2. Pilih tab **"Sumber Kamera (RTSP & M3U8)"**.
3. Klik **"Tambah Sumber Kamera"**:
   - Masukkan nama kamera (misal: *Gate Masuk Utama*) dan lokasi.
   - Masukkan URL stream (misal: `rtsp://admin:password@192.168.1.50:554/live` atau link `https://domain.com/stream.m3u8`).
   - Gunakan tombol **"Uji Koneksi"** untuk memverifikasi stream secara langsung.
4. Kamera yang aktif akan otomatis muncul di player dashboard utama (`/`) dengan opsi pemutaran langsung HLS atau proxy MJPEG backend serta tombol capture snapshot dan ALPR trigger.


### Gate Detection (Program Utama)

```bash
# Dari video
python gate_detection.py --video path/to/video.mp4

# Dari kamera
python gate_detection.py --camera 0

# Dengan OCR interval (setiap 5 frame)
python gate_detection.py --video video.mp4 --ocr-interval 5

# Custom gate duration (detik)
python gate_detection.py --video video.mp4 --gate-duration 60

# Custom model & confidence
python gate_detection.py --video video.mp4 --model ml/models/best.pt --conf 0.3
```

### Tombol Keyboard

| Tombol | Fungsi |
|--------|--------|
| `q` / `ESC` | Keluar |
| `p` | Pause / Resume |
| `+` / `-` | Naikkan / Turunkan confidence threshold |
| `r` | Reload database & reset lane |

### Struktur Database Plat

File `data/plate_database.json`:

```json
{
  "registered_plates": [
    {
      "plate": "T 1023 US",
      "owner": "Wakil Dekan",
      "vehicle": "Hyundai Stargazer",
      "color": "Putih",
      "active": true
    }
  ]
}
```

### Argumen Lengkap

| Argumen | Default | Deskripsi |
|---------|---------|-----------|
| `--video` | - | Path file video |
| `--camera` | - | Indeks kamera (0, 1, dst) |
| `--model` | `ml/models/best.pt` | Path model YOLO |
| `--conf` | `0.25` | Confidence threshold |
| `--imgsz` | `416` | Input size YOLO |
| `--ocr-interval` | `1` | Interval frame untuk OCR (1 = setiap frame) |
| `--gate-duration` | `120` | Durasi palang terbuka (detik) |
| `--db` | `data/plate_database.json` | Path database plat |
| `--loop` | - | Loop video secara continu |

## Struktur Proyek

```
smart-parking-system/
├── smartparking                   # Standalone All-in-One Go Binary (Web UI + Backend + ML)
├── gate_detection.py              # Dual lane gate controller & ALPR
├── api/                           # Backend API (FastAPI)
│   ├── routes/
│   │   ├── cameras.py             # RTSP/M3U8 camera management & streaming
│   │   ├── detection.py           # ALPR inference endpoints
│   │   ├── parking.py             # Parking slot endpoints
│   │   └── ...
│   └── models/
│       └── camera_source.py       # CameraSource DB model
├── web/                           # Frontend Dashboard (Next.js 14 + Tailwind CSS)
│   ├── components/monitoring/     # CameraPlayer & CameraSettings components
│   └── app/settings/              # Halaman konfigurasi kamera RTSP/M3U8 & ALPR
├── internal/                      # Go Standalone Engine (Supervisor, Gateway, Assets)
│   └── assets/                    # Embedded dist & ML models
├── ml/
│   ├── alpr/                      # YOLOv8 detector, OCR, preprocessor, pipeline
│   ├── slot_detection/            # Slot classification (MOG2/CNN) & validation
│   └── training/                  # Training pipelines & evaluation scripts
├── logic/
│   └── karnaugh.py                # Logika validasi cluster parkir (Karnaugh Map)
├── tests/                         # Unit tests (Pytest: API, OCR, ML, Cameras)
└── requirements.txt               # Python dependencies
```

## Cara Kerja

```
Video/Kamera
    │
    ▼
YOLOv8 Detection ──────► Bounding box plat nomor
    │
    ├──► center_x < mid_x ──► KIRI (LaneGate kiri)
    └──► center_x >= mid_x ─► KANAN (LaneGate kanan)
                                    │
                              ┌─────┴─────┐
                              │  PaddleOCR │
                              └─────┬─────┘
                                    │
                              db.match(ocr_text)
                                    │
                            ┌───────┴───────┐
                            │  Match found? │
                            └───────┬───────┘
                               Yes  │  No
                                │   │
                    ┌───────────┘   └──────────┐
                    ▼                          ▼
           PALANG TERBUKA              Tampilkan teks OCR
           (timer 120s)               tanpa info pemilik
           + info pemilik
```

## License

Dikembangkan untuk keperluan akademik.
