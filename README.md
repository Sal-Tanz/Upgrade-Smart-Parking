# Smart Parking System

Sistem manajemen parkir cerdas berbasis computer vision. Mendeteksi plat nomor kendaraan menggunakan YOLOv8 + PaddleOCR, mencocokkan dengan database terdaftar, dan mengontrol palang parkir secara otomatis untuk dual lane (kiri & kanan).

## Deskripsi

Program ini memproses video dari kamera/CCTV dan melakukan:

1. **Deteksi plat nomor** — YOLOv8 mendeteksi bounding box plat pada frame
2. **OCR plat nomor** — PaddleOCR membaca teks dari hasil crop plat
3. **Matching database** — Teks OCR dicocokkan ke `data/plate_database.json` (fuzzy match berdasarkan digit)
4. **Gate control** — Palang otomatis terbuka jika plat terdaftar, dengan timer (default 120 detik)
5. **Dual lane independen** — Layar terbagi kiri (60%) dan kanan (40%), masing-masing jalur memproses dan mengunci plat pertama yang terdeteksi secara terpisah

## Library

| Library | Versi | Kegunaan |
|---------|-------|----------|
| Python | 3.10+ | Runtime |
| PyTorch | 2.5+ | Inference backend YOLO |
| ultralytics | 8.4+ | YOLOv8 object detection |
| PaddleOCR | 2.9+ | OCR engine untuk membaca teks plat |
| PaddlePaddle | 2.5+ | Backend PaddleOCR |
| OpenCV | 4.8+ | Image/video processing & rendering |

Install semua dependencies:

```bash
pip install -r requirements.txt
```

## Instalasi

```bash
# Clone repository
git clone https://github.com/Sal-Tanz/Machine-Learning-Parking.git
cd Machine-Learning-Parking

# (Opsional) Buat virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Penggunaan

### Menjalankan Backend API & Frontend Web UI Sekaligus

Anda dapat menjalankan FastAPI backend (`http://localhost:8000`) dan Next.js frontend (`http://localhost:3000`) secara bersamaan dalam satu command:

```bash
# Menggunakan Bash script (Linux / macOS)
./start.sh

# ATAU menggunakan Python script (Cross-platform / Windows / Linux / macOS)
python run.py
```

Script ini secara otomatis akan:
- Membuat file `.env` dari `.env.example` jika belum tersedia.
- Menjalankan Backend API FastAPI pada port `8000` (`http://localhost:8000`, API Docs di `http://localhost:8000/docs`).
- Menjalankan Frontend Next.js Web UI pada port `3000` (`http://localhost:3000`).
- Menghentikan kedua layanan secara bersih saat menekan `Ctrl+C`.


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
Machine-Learning-Parking/
├── gate_detection.py              # Program utama: dual lane gate control
├── ml/
│   ├── alpr/
│   │   ├── detector.py            # YOLOv8 plate detection
│   │   ├── ocr.py                 # PaddleOCR / EasyOCR
│   │   ├── pipeline.py            # End-to-end ALPR pipeline
│   │   └── preprocessor.py        # Image preprocessing
│   └── models/
│       └── best.pt                # Model YOLO trained
├── data/
│   ├── plate_database.json        # Database plat terdaftar
│   └── slot_config.json           # Konfigurasi slot parkir
├── api/                           # Backend API (FastAPI)
├── web/                           # Frontend (Next.js 14)
├── logic/
│   └── karnaugh.py                # Logika validasi cluster parkir
├── tests/                         # Unit tests
├── output/                        # Laporan & debug output
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
