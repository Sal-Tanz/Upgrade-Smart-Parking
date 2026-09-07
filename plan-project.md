# Plan Pengembangan Sistem Machine Learning Manajemen Parkir Cerdas

> **Versi:** 1.1  
> **Scope:** Sistem terintegrasi deteksi plat nomor, deteksi area parkir, notifikasi IoT ESP32, pemodelan logika Karnaugh Map, dan Web UI (mobile-friendly)  
> **Target:** Parkir kampus berbasis hak akses jabatan (Dekan, Wakil Dekan, Dosen)

---

## Daftar Isi

1. [Gambaran Umum Sistem](#1-gambaran-umum-sistem)
2. [Modul 1 — Deteksi & Validasi Plat Nomor Kendaraan](#2-modul-1--deteksi--validasi-plat-nomor-kendaraan)
3. [Modul 2 — Deteksi Area & Garis Parkir](#3-modul-2--deteksi-area--garis-parkir)
4. [Modul 3 — Notifikasi Buzzer via IoT ESP32](#4-modul-3--notifikasi-buzzer-via-iot-esp32)
5. [Modul 4 — Pemodelan Karnaugh Map](#5-modul-4--pemodelan-karnaugh-map)
6. [Modul 5 — Web UI (Pendaftaran, Training & Monitoring)](#6-modul-5--web-ui-pendaftaran-training--monitoring)
7. [Arsitektur Sistem Terintegrasi](#7-arsitektur-sistem-terintegrasi)
8. [Stack Teknologi](#8-stack-teknologi)
9. [Rencana Implementasi & Timeline](#9-rencana-implementasi--timeline)
10. [Struktur Direktori Proyek](#10-struktur-direktori-proyek)

---

## 1. Gambaran Umum Sistem

Sistem parkir cerdas ini menggabungkan **Computer Vision**, **Machine Learning**, **Logika Digital**, dan **IoT** dalam satu pipeline terintegrasi. Sistem mengelola hak akses parkir berdasarkan jabatan dan memastikan kendaraan parkir di zona yang sesuai.

### Alur Kerja Utama

```
Kendaraan Masuk
      │
      ▼
[Kamera] ──► [Deteksi Plat Nomor (ALPR/OCR)]
                        │
                        ▼
              [Validasi Database Plat]
                    /         \
               Terdaftar    Tidak Terdaftar
                  │                │
                  ▼                ▼
       [Identifikasi Jabatan]   [Buzzer ALERT]
       D / W / S                [Tolak Akses]
                  │
                  ▼
       [Karnaugh Map Logic]
       M = D + W  |  O = D + W + S
                  │
                  ▼
       [Tentukan Cluster Parkir]
       Merah (VIP) / Orange (Umum Kampus)
                  │
                  ▼
       [Deteksi Area Parkir (CV)]
       Cek slot kosong di cluster yg sesuai
                  │
                  ▼
       [Validasi Posisi Kendaraan]
       Parkir sesuai cluster? ──► Tidak ──► [Buzzer WARNING]
                  │
                 Ya
                  ▼
       [Catat Log & Update Status Slot]
```

---

## 2. Modul 1 — Deteksi & Validasi Plat Nomor Kendaraan

### 2.1 Tujuan

Mendeteksi plat nomor kendaraan secara otomatis dari kamera, mengekstrak teks plat, dan memvalidasi apakah kendaraan terdaftar serta menentukan hak akses cluster parkir.

### 2.2 Pipeline Deteksi Plat Nomor

#### Tahap 1 — Object Detection (Lokalisasi Plat)

- **Model:** YOLOv8 (You Only Look Once v8) fine-tuned untuk deteksi plat nomor Indonesia
- **Input:** Frame video dari kamera IP (resolusi min. 1080p)
- **Output:** Bounding box koordinat area plat nomor
- **Dataset Training:**
  - Dataset plat nomor Indonesia (minimal 5.000 gambar)
  - Augmentasi: rotasi ±15°, variasi pencahayaan, blur, noise
  - Split: 80% train / 10% validation / 10% test
- **Target mAP:** ≥ 0.90 pada IoU 0.5

#### Tahap 2 — OCR / Text Recognition (Baca Teks Plat)

- **Model:** PaddleOCR atau EasyOCR dengan fine-tuning pada karakter plat Indonesia
- **Pre-processing sebelum OCR:**
  - Crop region dari hasil YOLO
  - Grayscale conversion
  - Adaptive thresholding (binarisasi)
  - Deskew / perspective correction
  - Super-resolution (ESRGAN) jika resolusi rendah
- **Output:** String teks plat nomor (contoh: `B 1234 XYZ`)
- **Post-processing:**
  - Normalisasi format (hapus spasi ekstra, uppercase)
  - Regex pattern matching untuk validasi format plat Indonesia

#### Tahap 3 — Validasi Database

```python
# Pseudocode validasi plat
def validate_plate(plate_text: str) -> dict:
    plate_normalized = normalize(plate_text)
    record = database.query("SELECT * FROM kendaraan WHERE plat = ?", plate_normalized)
    
    if not record:
        return {"status": "REJECTED", "reason": "Plat tidak terdaftar", "trigger_buzzer": True}
    
    return {
        "status": "ACCEPTED",
        "jabatan": record.jabatan,   # "D", "W", atau "S"
        "cluster": compute_cluster(record.jabatan),
        "trigger_buzzer": False
    }
```

### 2.3 Struktur Database Kendaraan

```sql
CREATE TABLE kendaraan (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    plat        VARCHAR(15) UNIQUE NOT NULL,
    nama_pemilik VARCHAR(100),
    jabatan     ENUM('D', 'W', 'S') NOT NULL,  -- Dekan, Wakil Dekan, Dosen
    cluster_hak ENUM('Merah', 'Orange') NOT NULL,
    aktif       BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.4 Kondisi Trigger Buzzer — Modul 1

| Kondisi | Status | Aksi Buzzer |
|---|---|---|
| Plat tidak terdaftar di DB | REJECTED | ALERT panjang (3x) |
| Plat terdaftar, jabatan valid | ACCEPTED | Tidak berbunyi |
| Gagal baca plat (confidence < threshold) | RETRY | Buzzer pendek (1x), ulangi scan |

---

## 3. Modul 2 — Deteksi Area & Garis Parkir

### 3.1 Tujuan

Mendeteksi slot parkir (kosong/terisi) secara real-time menggunakan kamera pengawas di atas area parkir, dan memvalidasi apakah kendaraan parkir di cluster yang sesuai dengan hak aksesnya.

### 3.2 Pipeline Deteksi Area Parkir

#### Tahap 1 — Segmentasi Garis Parkir

- **Metode Awal (Setup):** Deteksi garis menggunakan Hough Line Transform (OpenCV) untuk memetakan koordinat setiap slot parkir
- **Output Setup:** File konfigurasi JSON berisi polygon koordinat tiap slot
- **Label Cluster:** Setiap slot diberi label `Merah` atau `Orange` dalam konfigurasi

```json
{
  "slots": [
    {"id": "M-01", "cluster": "Merah", "polygon": [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]},
    {"id": "M-02", "cluster": "Merah", "polygon": [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]},
    {"id": "O-01", "cluster": "Orange", "polygon": [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]}
  ]
}
```

#### Tahap 2 — Klasifikasi Slot (Kosong / Terisi)

- **Model:** CNN ringan (MobileNetV3 atau EfficientNet-Lite) untuk klasifikasi per-slot
- **Input:** Crop gambar tiap slot dari kamera top-down
- **Output:** `0 = Kosong` / `1 = Terisi`
- **Alternatif tanpa kamera baru:** Background Subtraction (MOG2) + analisis pixel ratio
- **Dataset Training:**
  - Minimal 2.000 gambar per kelas (kosong/terisi)
  - Kondisi: siang/malam, hujan, bayangan
  - Augmentasi: flip, brightness jitter, random crop

#### Tahap 3 — Validasi Posisi Kendaraan

Setelah kendaraan parkir, sistem memeriksa apakah kendaraan berada di cluster yang sesuai berdasarkan plat yang terdeteksi:

```python
def validate_parking_position(plate_text: str, detected_slot_id: str) -> dict:
    vehicle = database.get_vehicle(plate_text)
    slot = slot_config.get_slot(detected_slot_id)
    
    if vehicle.cluster_hak == slot.cluster:
        return {"valid": True, "trigger_buzzer": False}
    else:
        return {
            "valid": False,
            "reason": f"Kendaraan {vehicle.jabatan} parkir di cluster {slot.cluster}",
            "trigger_buzzer": True,
            "buzzer_type": "WARNING"
        }
```

### 3.3 Kondisi Trigger Buzzer — Modul 2

| Kondisi | Trigger Buzzer |
|---|---|
| Slot kosong di cluster yang benar tersedia | Tidak |
| Kendaraan parkir di cluster yang salah | WARNING (2x sedang) |
| Semua slot cluster yang berhak penuh | INFO (1x pendek) |

---

## 4. Modul 3 — Notifikasi Buzzer via IoT ESP32

### 4.1 Arsitektur IoT

```
[Server ML] ──► [MQTT Broker] ──► [ESP32] ──► [Buzzer + LED]
                                        │
                                    [LCD/OLED Display]
```

### 4.2 Komponen Hardware ESP32

| Komponen | Fungsi |
|---|---|
| ESP32 DevKit | Mikrokontroler utama + WiFi |
| Active Buzzer 5V | Notifikasi suara |
| LED Merah / Hijau | Indikator visual |
| OLED 128x64 (I2C) | Tampilkan info plat & status |
| Power Supply 5V/2A | Daya sistem |

### 4.3 Protokol Komunikasi — MQTT

**Topic MQTT yang digunakan:**

```
parking/buzzer/alert     ← Server → ESP32 (jenis alarm)
parking/slot/status      ← ESP32 → Server (status slot real-time)
parking/vehicle/entry    ← ESP32 → Server (deteksi kendaraan masuk)
```

**Payload format (JSON):**

```json
{
  "action": "ALERT",
  "type": "REJECTED",
  "plate": "B 1234 XYZ",
  "reason": "Plat tidak terdaftar",
  "buzzer_pattern": "LONG_3X",
  "timestamp": "2025-01-01T08:00:00Z"
}
```

### 4.4 Pola Buzzer

| Kode | Pola | Kondisi |
|---|---|---|
| `SHORT_1X` | Bip pendek sekali | Retry scan plat |
| `LONG_3X` | Bip panjang 3x | Plat tidak terdaftar (REJECTED) |
| `MEDIUM_2X` | Bip sedang 2x | Parkir di cluster salah (WARNING) |
| `SHORT_DOUBLE` | 2 bip cepat | Slot cluster penuh |
| `SUCCESS_TONE` | Bip naik singkat | Kendaraan valid & parkir benar |

### 4.5 Kode Firmware ESP32 (Arduino / ESP-IDF)

```cpp
// Pseudocode utama ESP32
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

#define BUZZER_PIN   25
#define LED_RED      26
#define LED_GREEN    27

void handleMQTTMessage(char* topic, byte* payload, unsigned int length) {
    StaticJsonDocument<256> doc;
    deserializeJson(doc, payload, length);
    
    String action = doc["action"];
    String type   = doc["type"];
    
    if (action == "ALERT") {
        triggerBuzzer(doc["buzzer_pattern"]);
        updateLED(type);
        updateDisplay(doc["plate"], doc["reason"]);
    }
    
    if (action == "SUCCESS") {
        digitalWrite(LED_GREEN, HIGH);
        triggerBuzzer("SUCCESS_TONE");
        updateDisplay(doc["plate"], "Parkir Valid");
        delay(3000);
        digitalWrite(LED_GREEN, LOW);
    }
}

void triggerBuzzer(String pattern) {
    if (pattern == "LONG_3X") {
        for (int i = 0; i < 3; i++) {
            tone(BUZZER_PIN, 1000, 800);
            delay(1200);
        }
    } else if (pattern == "MEDIUM_2X") {
        for (int i = 0; i < 2; i++) {
            tone(BUZZER_PIN, 1500, 400);
            delay(700);
        }
    }
    // ... pola lainnya
}
```

### 4.6 Alur Validasi Terintegrasi (ML ↔ ESP32)

```
1. Kamera deteksi kendaraan masuk
         │
2. ML Server: ALPR → OCR → Validasi DB
         │
3. ML Server: Cek cluster & slot availability
         │
4. Hasil dikirim ke MQTT Broker
         │
5. ESP32 subscribe MQTT → eksekusi aksi:
   ├── Valid & Cluster Benar → LED Hijau + SUCCESS_TONE
   ├── Tidak Terdaftar      → LED Merah + LONG_3X
   └── Salah Cluster        → LED Merah + MEDIUM_2X
```

---

## 5. Modul 4 — Pemodelan Karnaugh Map

### 5.1 Definisi Input & Output

Berdasarkan dokumen pemodelan yang disertakan:

**Input (Jabatan):**

| Simbol | Keterangan |
|---|---|
| D | Dekan |
| W | Wakil Dekan |
| S | Dosen (Staff) |

**Output (Cluster Parkir):**

| Output | Kondisi Aktif |
|---|---|
| M (Cluster Merah) | Dekan atau Wakil Dekan |
| O (Cluster Orange) | Dekan, Wakil Dekan, atau Dosen |

### 5.2 Tabel Kebenaran

| D | W | S | Cluster Merah (M) | Cluster Orange (O) |
|---|---|---|---|---|
| 0 | 0 | 0 | 0 | 0 |
| 0 | 0 | 1 | 0 | 1 |
| 0 | 1 | 0 | 1 | 1 |
| 0 | 1 | 1 | 1 | 1 |
| 1 | 0 | 0 | 1 | 1 |
| 1 | 0 | 1 | 1 | 1 |
| 1 | 1 | 0 | 1 | 1 |
| 1 | 1 | 1 | 1 | 1 |

### 5.3 Karnaugh Map — Cluster Merah (M)

Cluster Merah aktif jika yang parkir adalah **Dekan atau Wakil Dekan**.

```
K-Map M (Cluster Merah):

         WS
    D  | 00 | 01 | 11 | 10 |
   ----+----+----+----+----+
    0  |  0 |  0 |  1 |  1 |   ← Grup W (kolom 11, 10)
   ----+----+----+----+----+
    1  |  1 |  1 |  1 |  1 |   ← Grup D (seluruh baris 1)
   ----+----+----+----+----+

Grup 1: Baris D=1 → semua kolom → D
Grup 2: Kolom WS=10 dan WS=11 (W=1) di baris D=0 → W
```

**Persamaan Boolean Disederhanakan:**

```
M = D + W
```

> Cluster Merah aktif jika Dekan = 1 ATAU Wakil Dekan = 1

### 5.4 Karnaugh Map — Cluster Orange (O)

Cluster Orange aktif jika yang parkir adalah **Dekan, Wakil Dekan, atau Dosen**.

```
K-Map O (Cluster Orange):

         WS
    D  | 00 | 01 | 11 | 10 |
   ----+----+----+----+----+
    0  |  0 |  1 |  1 |  1 |   ← Grup S, Grup W
   ----+----+----+----+----+
    1  |  1 |  1 |  1 |  1 |   ← Grup D
   ----+----+----+----+----+

Grup 1: Baris D=1 → semua kolom → D
Grup 2: Kolom WS=11 dan WS=10 (W=1) → W
Grup 3: Kolom WS=11 dan WS=01 (S=1) di baris D=0 → S (dikombinasikan)
```

**Persamaan Boolean Disederhanakan:**

```
O = D + W + S
```

> Cluster Orange aktif jika Dekan = 1 ATAU Wakil Dekan = 1 ATAU Dosen = 1

### 5.5 Kesimpulan Logika Cluster

```
M = D + W
O = D + W + S
```

| Jabatan | Cluster Merah (M) | Cluster Orange (O) |
|---|---|---|
| Dekan (D=1) | ✅ Aktif | ✅ Aktif |
| Wakil Dekan (W=1) | ✅ Aktif | ✅ Aktif |
| Dosen (S=1) | ❌ Tidak Aktif | ✅ Aktif |
| Tamu / Tidak Terdaftar | ❌ Tidak Aktif | ❌ Tidak Aktif |

### 5.6 Implementasi Logika K-Map dalam Kode

```python
# Implementasi langsung dari persamaan K-Map
def compute_cluster(jabatan: str) -> str | None:
    """
    Menentukan cluster parkir berdasarkan persamaan Karnaugh Map.
    M = D + W
    O = D + W + S
    """
    D = 1 if jabatan == "D" else 0   # Dekan
    W = 1 if jabatan == "W" else 0   # Wakil Dekan
    S = 1 if jabatan == "S" else 0   # Dosen

    M = D or W          # Cluster Merah: M = D + W
    O = D or W or S     # Cluster Orange: O = D + W + S

    if M:
        return "Merah"   # Prioritas tertinggi: Dekan & Wakil Dekan
    elif O:
        return "Orange"  # Dosen
    else:
        return None      # Tidak berhak parkir

def validate_cluster_access(jabatan: str, slot_cluster: str) -> bool:
    """Validasi apakah jabatan boleh parkir di cluster tertentu."""
    allowed_cluster = compute_cluster(jabatan)
    
    # Cluster Merah bisa parkir di Orange jika Merah penuh (opsional kebijakan)
    if allowed_cluster == "Merah" and slot_cluster in ["Merah", "Orange"]:
        return True
    return allowed_cluster == slot_cluster
```

---

## 6. Modul 5 — Web UI (Pendaftaran, Training & Monitoring)

### 6.1 Tujuan

Menyediakan antarmuka web yang responsif (mobile-friendly) untuk:
1. **Pendaftaran plat nomor** kendaraan untuk dataset training ALPR
2. **Pendaftaran garis area parkir** (polygon) untuk dataset training slot detection
3. **Monitoring real-time** capture kejadian pelanggaran parkir
4. **Akses mobile** untuk kemudahan pendaftaran dan monitoring dari mana saja

### 6.2 Fitur 1 — Pendaftaran Plat Nomor untuk Training

Memungkinkan operator/admin mendaftarkan gambar plat nomor kendaraan beserta labelnya untuk memperkaya dataset training model ALPR.

#### Alur Pendaftaran Plat

```
[User buka halaman Pendaftaran Plat]
         │
         ▼
[Upload foto plat / Capture via kamera HP]
         │
         ▼
[Preview gambar + Crop area plat (jika perlu)]
         │
         ▼
[Input metadata:]
  ├── Teks plat nomor (ground truth label)
  ├── Jenis kendaraan
  ├── Kondisi pencahayaan (siang/malam/hujan)
  └── Sudut pengambilan (depan/belakang/miring)
         │
         ▼
[Simpan ke dataset training]
  ├── Gambar → storage/ml_dataset/plates/
  ├── Label → database tabel plate_annotations
  └── Auto-split ke train/val/test (80/10/10)
```

#### Skema Database — Anotasi Plat

```sql
CREATE TABLE plate_annotations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    image_path      VARCHAR(255) NOT NULL,
    plate_text      VARCHAR(15) NOT NULL,          -- ground truth label
    vehicle_type    VARCHAR(50),                    -- mobil/motor/truk
    lighting        ENUM('siang','malam','hujan','mendung') DEFAULT 'siang',
    angle           ENUM('depan','belakang','miring') DEFAULT 'depan',
    bbox_x          FLOAT,                         -- bounding box x (normalisasi 0-1)
    bbox_y          FLOAT,                         -- bounding box y (normalisasi 0-1)
    bbox_w          FLOAT,                         -- bounding box width
    bbox_h          FLOAT,                         -- bounding box height
    split           ENUM('train','val','test') DEFAULT 'train',
    annotated_by    VARCHAR(100),
    is_verified     BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_plate_text ON plate_annotations(plate_text);
CREATE INDEX idx_plate_split ON plate_annotations(split);
```

#### Komponen UI — Halaman Pendaftaran Plat

| Komponen | Deskripsi | Mobile Support |
|---|---|---|
| Upload Area | Drag & drop atau tap untuk upload gambar | ✅ Touch-friendly, support kamera HP |
| Image Cropper | Crop area plat nomor pada gambar | ✅ Pinch-to-zoom, gesture support |
| Form Metadata | Input teks plat, jenis kendaraan, kondisi | ✅ Responsive form layout |
| Preview Card | Preview gambar + label sebelum submit | ✅ Card layout adaptif |
| Batch Upload | Upload multiple gambar sekaligus (zip/multi-select) | ✅ Mobile file picker |
| Progress Bar | Progress upload & penyimpanan | ✅ Animated progress |
| History Table | Riwayat plat yang sudah didaftarkan | ✅ Scrollable table → card view di mobile |

### 6.3 Fitur 2 — Pendaftaran Garis Area Parkir untuk Training

Memungkinkan operator menggambar polygon garis area parkir langsung di atas gambar dari kamera CCTV/top-down untuk dataset training slot detection dan konfigurasi slot.

#### Alur Pendaftaran Area Parkir

```
[User buka halaman Pendaftaran Area Parkir]
         │
         ▼
[Upload gambar area parkir dari CCTV / screenshot live feed]
         │
         ▼
[Canvas editor muncul dengan gambar sebagai background]
         │
         ▼
[User menggambar polygon slot parkir:]
  ├── Tap/klik titik-titik polygon (4 titik = 1 slot)
  ├── Auto-snap ke garis (opsional, bantuan edge detection)
  ├── Label slot: ID (M-01, O-01, dst.)
  └── Assign cluster: Merah / Orange
         │
         ▼
[Preview semua slot yang sudah ditandai]
         │
         ▼
[Simpan konfigurasi:]
  ├── Koordinat polygon → slot_config.json (runtime)
  ├── Gambar + anotasi → dataset training slot_classifier
  └── Metadata → database tabel parking_slot_annotations
```

#### Skema Database — Anotasi Area Parkir

```sql
CREATE TABLE parking_slot_annotations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    image_path      VARCHAR(255) NOT NULL,          -- gambar source (CCTV frame)
    slot_id         VARCHAR(10) NOT NULL,            -- M-01, O-01, dst.
    cluster         ENUM('Merah','Orange') NOT NULL,
    polygon_points  TEXT NOT NULL,                   -- JSON array [[x1,y1],[x2,y2],...]
    slot_status     ENUM('kosong','terisi','unknown') DEFAULT 'unknown',  -- ground truth label
    camera_id       VARCHAR(50),                     -- ID kamera sumber
    capture_time    TIMESTAMP,                       -- waktu capture gambar
    annotated_by    VARCHAR(100),
    is_verified     BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE camera_sources (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    camera_name     VARCHAR(100) NOT NULL,
    stream_url      VARCHAR(255),                   -- RTSP/HTTP stream URL
    location        VARCHAR(200),
    resolution_w    INTEGER DEFAULT 1920,
    resolution_h    INTEGER DEFAULT 1080,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Komponen UI — Canvas Editor Area Parkir

| Komponen | Deskripsi | Mobile Support |
|---|---|---|
| Image Canvas | Area gambar tempat menggambar polygon | ✅ Touch draw, pinch zoom |
| Polygon Tool | Alat gambar polygon (tap titik, drag, close shape) | ✅ Touch-friendly vertices |
| Slot Labeler | Popup label saat polygon selesai (ID + cluster) | ✅ Bottom sheet di mobile |
| Snap-to-Edge | Bantuan otomatis snap ke garis parkir (Canny edge) | ✅ Toggle on/off |
| Slot List Panel | Daftar semua slot yang sudah ditandai | ✅ Collapsible, bottom drawer |
| Color Coding | Warna berbeda untuk cluster Merah vs Orange | ✅ High contrast colors |
| Undo/Redo | Batalkan/ulangi langkah menggambar | ✅ Gesture (2-finger tap = undo) |
| Export Config | Export ke slot_config.json | ✅ Download/share |
| Capture Live | Ambil frame langsung dari live CCTV feed | ✅ Tap to capture |

### 6.4 Fitur 3 — Monitoring Capture & Pelanggaran Parkir

Dashboard real-time untuk memantau semua kejadian yang terdeteksi sistem, termasuk pelanggaran parkir, kendaraan tidak terdaftar, dan status slot.

#### Jenis Kejadian yang Dimonitor

| Jenis Kejadian | Kode | Prioritas | Warna Badge |
|---|---|---|---|
| Kendaraan tidak terdaftar | `UNREGISTERED` | 🔴 Tinggi | Merah |
| Parkir di cluster salah | `WRONG_CLUSTER` | 🔴 Tinggi | Merah |
| Gagal baca plat nomor | `PLATE_READ_FAIL` | 🟡 Sedang | Kuning |
| Slot cluster penuh | `CLUSTER_FULL` | 🟡 Sedang | Kuning |
| Parkir valid & benar | `VALID_PARKING` | 🟢 Rendah | Hijau |
| Kendaraan keluar | `VEHICLE_EXIT` | ⚪ Info | Abu-abu |
| Kamera offline | `CAMERA_OFFLINE` | 🔴 Tinggi | Merah |
| ESP32 disconnect | `IOT_DISCONNECT` | 🔴 Tinggi | Merah |

#### Layout Dashboard Monitoring

```
┌──────────────────────────────────────────────────────────────┐
│  🅿️ SISTEM MONITORING PARKIR CERDAS          [🔔 3] [👤 Admin] │
├──────────────────────┬───────────────────────────────────────┤
│                      │                                       │
│  📊 Ringkasan        │  📡 Live Feed (Kamera)                │
│  ┌────────────────┐  │  ┌─────────────────────────────────┐  │
│  │ Total Slot: 20 │  │  │                                 │  │
│  │ Terisi:    12  │  │  │    [Live CCTV Feed Player]      │  │
│  │ Kosong:     8  │  │  │                                 │  │
│  │ Pelanggaran: 3 │  │  │    Overlay: bounding box plat   │  │
│  └────────────────┘  │  │    + status slot (hijau/merah)  │  │
│                      │  │    + alert animation            │  │
│  🗺️ Peta Slot        │  └─────────────────────────────────┘  │
│  ┌────────────────┐  │                                       │
│  │ [M-01] 🟢     │  │  📋 Log Kejadian Real-time             │
│  │ [M-02] 🔴     │  │  ┌─────────────────────────────────┐  │
│  │ [M-03] 🟢     │  │  │ 🔴 08:15 | B 9999 QQ            │  │
│  │ [O-01] 🔴     │  │  │    UNREGISTERED - Plat tdk       │  │
│  │ [O-02] 🟢     │  │  │    terdaftar → Buzzer LONG_3X    │  │
│  │ [O-03] 🟡     │  │  ├─────────────────────────────────┤  │
│  │  ...           │  │  │ 🟡 08:12 | D 4567 AB            │  │
│  └────────────────┘  │  │    WRONG_CLUSTER - Dekan parkir  │  │
│                      │  │    di Orange → Buzzer MEDIUM_2X  │  │
│  📈 Statistik Hari   │  ├─────────────────────────────────┤  │
│  ┌────────────────┐  │  │ 🟢 08:10 | B 1234 XYZ           │  │
│  │ [Chart: jumlah │  │  │    VALID_PARKING - Slot M-01     │  │
│  │  kendaraan per │  │  │    → SUCCESS_TONE                │  │
│  │  jam]          │  │  └─────────────────────────────────┘  │
│  └────────────────┘  │                                       │
├──────────────────────┴───────────────────────────────────────┤
│  📱 Bottom Navigation (Mobile): [Dashboard] [Slots] [Log]    │
└──────────────────────────────────────────────────────────────┘
```

#### Skema Database — Log Kejadian

```sql
CREATE TABLE parking_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type      VARCHAR(30) NOT NULL,           -- UNREGISTERED, WRONG_CLUSTER, dll.
    priority        ENUM('high','medium','low','info') DEFAULT 'low',
    plate_text      VARCHAR(15),
    vehicle_jabatan VARCHAR(5),                     -- D, W, S, atau NULL
    slot_id         VARCHAR(10),
    cluster_detected VARCHAR(10),
    cluster_expected VARCHAR(10),
    camera_id       VARCHAR(50),
    capture_image   VARCHAR(255),                   -- path gambar bukti
    confidence      FLOAT,                          -- confidence score deteksi
    buzzer_triggered BOOLEAN DEFAULT FALSE,
    buzzer_pattern  VARCHAR(20),
    resolved        BOOLEAN DEFAULT FALSE,
    resolved_by     VARCHAR(100),
    resolved_at     TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_event_type ON parking_events(event_type);
CREATE INDEX idx_event_created ON parking_events(created_at DESC);
CREATE INDEX idx_event_plate ON parking_events(plate_text);
```

#### API Endpoint untuk Monitoring (WebSocket + REST)

```python
# FastAPI WebSocket endpoint — real-time event stream
@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    await websocket.accept()
    async for event in event_bus.subscribe("parking_events"):
        await websocket.send_json({
            "type": event.event_type,
            "plate": event.plate_text,
            "slot": event.slot_id,
            "priority": event.priority,
            "image_url": f"/api/captures/{event.capture_image}",
            "timestamp": event.created_at.isoformat(),
            "buzzer": event.buzzer_pattern
        })

# REST endpoint — riwayat kejadian dengan filter & pagination
@router.get("/api/events")
async def get_events(
    event_type: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    page: int = 1,
    per_page: int = 20
):
    ...

# REST endpoint — capture image (bukti pelanggaran)
@router.get("/api/captures/{filename}")
async def get_capture(filename: str):
    ...

# REST endpoint — statistik dashboard
@router.get("/api/stats/today")
async def get_today_stats():
    return {
        "total_slots": ...,
        "occupied": ...,
        "available": ...,
        "violations_today": ...,
        "vehicles_today": ...,
        "hourly_chart": [...]
    }
```

### 6.5 Fitur 4 — Monitoring Kehadiran & Ketepatan Waktu

Dashboard laporan kedatangan dan kepulangan kendaraan terdaftar dengan evaluasi ketepatan waktu berdasarkan jadwal yang telah ditentukan.

#### Konsep Dasar

Setiap kendaraan terdaftar dapat memiliki **jadwal forventif** (jam masuk & jam keluar). Sistem otomatis mencatat waktu kedatangan dan kepulangan dari deteksi plat nomor, lalu membandingkannya dengan jadwal untuk menentukan status ketepatan waktu.

#### Alur Monitoring Kehadiran

```
[Kamera deteksi plat nomor]
         │
         ▼
[ALPR → Identifikasi plat terdaftar]
         │
         ▼
[Cek: Plat sudah ada di area parkir hari ini?]
         │
    ┌────┴────┐
    │ Tidak   │ Ya (sudah tercatat masuk)
    ▼         ▼
[Catat ARRIVAL]         [Catat DEPARTURE]
  ├── Timestamp masuk     ├── Timestamp keluar
  ├── Ambil jam_jadwal    ├── Ambil jam_jadwal keluar
  │   masuk dari schedule │   dari schedule
  ├── Hitung selisih      ├── Hitung selisih
  │                       │
  ▼                       ▼
[Tentukan Status]        [Tentukan Status]
  ├── TEPAT_WAKTU         ├── TEPAT_WAKTU
  ├── TERLAMBAT           ├── PULANG_CEPAT
  └── TIDAK_ADA_JADWAL   ├── PULANG_LEMBUR
                         └── TIDAK_ADA_JADWAL
         │                       │
         ▼                       ▼
[Simpan ke attendance_log + Parking Event]
         │
         ▼
[Update Dashboard Kehadiran]
```

#### Skema Database — Jadwal Kendaraan

```sql
CREATE TABLE vehicle_schedules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id      INTEGER NOT NULL,                   -- FK ke kendaraan
    day_of_week     INTEGER NOT NULL,                   -- 0=Minggu, 1=Senin, ... 6=Sabtu
    expected_arrival TIME,                               -- jam masuk forventif (contoh: 07:30)
    expected_departure TIME,                             -- jam keluar forventif (contoh: 16:00)
    tolerance_minutes INTEGER DEFAULT 15,               -- toleransi keterlambatan (menit)
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vehicle_id) REFERENCES kendaraan(id),
    UNIQUE(vehicle_id, day_of_week)
);

-- Contoh data jadwal:
-- vehicle_id=1 (Dekan, B 1234 ABC), Senin, masuk 07:30, pulang 16:00, toleransi 15 menit
-- vehicle_id=2 (Dosen, D 5678 XYZ), Senin-Jumat, masuk 08:00, pulang 15:00, toleransi 30 menit
```

#### Skema Database — Log Kehadiran

```sql
CREATE TABLE attendance_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id      INTEGER NOT NULL,                   -- FK ke kendaraan
    plate_text      VARCHAR(15) NOT NULL,
    tanggal         DATE NOT NULL,                       -- tanggal kehadiran
    day_of_week     INTEGER NOT NULL,                   -- hari (0-6)

    -- Kedatangan
    arrival_time    TIMESTAMP,                           -- waktu tiba (dari deteksi kamera)
    arrival_slot_id VARCHAR(10),                        -- slot parkir yang digunakan
    arrival_status  ENUM('TEPAT_WAKTU','TERLAMBAT','TIDAK_ADA_JADWAL') DEFAULT 'TIDAK_ADA_JADWAL',
    arrival_scheduled TIME,                             -- jadwal masuk forventif
    arrival_diff_minutes INTEGER,                       -- selisih menit (+ = terlambat)
    arrival_capture_image VARCHAR(255),                 -- path gambar bukti masuk

    -- Kepulangan
    departure_time  TIMESTAMP,                           -- waktu pulang (dari deteksi kamera)
    departure_status ENUM('TEPAT_WAKTU','PULANG_CEPAT','PULANG_LEMBUR','TIDAK_ADA_JADWAL') DEFAULT 'TIDAK_ADA_JADWAL',
    departure_scheduled TIME,                           -- jadwal keluar forventif
    departure_diff_minutes INTEGER,                     -- selisih menit (- = pulang cepat, + = lembur)
    departure_capture_image VARCHAR(255),               -- path gambar bukti keluar

    -- Durasi & status keseluruhan
    parking_duration_minutes INTEGER,                   -- total menit parkir
    status_hari     ENUM('HADIR','IZIN','SAKIT','ALPA','BELUM_MASUK') DEFAULT 'BELUM_MASUK',

    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (vehicle_id) REFERENCES kendaraan(id)
);

CREATE UNIQUE INDEX idx_attendance_vehicle_date ON attendance_log(vehicle_id, tanggal);
CREATE INDEX idx_attendance_tanggal ON attendance_log(tanggal);
CREATE INDEX idx_attendance_status ON attendance_log(status_hari);
CREATE INDEX idx_attendance_arrival_status ON attendance_log(arrival_status);
```

#### Logika Penentuan Status Ketepatan Waktu

```python
from datetime import time, datetime, timedelta
from enum import Enum

class ArrivalStatus(Enum):
    TEPAT_WAKTU = "TEPAT_WAKTU"
    TERLAMBAT = "TERLAMBAT"
    TIDAK_ADA_JADWAL = "TIDAK_ADA_JADWAL"

class DepartureStatus(Enum):
    TEPAT_WAKTU = "TEPAT_WAKTU"
    PULANG_CEPAT = "PULANG_CEPAT"
    PULANG_LEMBUR = "PULANG_LEMBUR"
    TIDAK_ADA_JADWAL = "TIDAK_ADA_JADWAL"

def evaluate_arrival(actual_time: datetime, schedule: dict) -> dict:
    """
    Evaluasi ketepatan waktu kedatangan.
    
    schedule = {
        'expected_arrival': time(7, 30),
        'tolerance_minutes': 15
    }
    """
    if not schedule or not schedule.get('expected_arrival'):
        return {"status": ArrivalStatus.TIDAK_ADA_JADWAL, "diff_minutes": None}

    expected = schedule['expected_arrival']
    tolerance = schedule.get('tolerance_minutes', 15)

    # Konversi ke menit dari midnight untuk perbandingan
    actual_minutes = actual_time.hour * 60 + actual_time.minute
    expected_minutes = expected.hour * 60 + expected.minute
    diff = actual_minutes - expected_minutes   # positif = terlambat

    if diff <= tolerance:
        status = ArrivalStatus.TEPAT_WAKTU
    else:
        status = ArrivalStatus.TERLAMBAT

    return {"status": status, "diff_minutes": diff}


def evaluate_departure(actual_time: datetime, schedule: dict) -> dict:
    """
    Evaluasi ketepatan waktu kepulangan.
    
    schedule = {
        'expected_departure': time(16, 0),
        'tolerance_minutes': 15
    }
    """
    if not schedule or not schedule.get('expected_departure'):
        return {"status": DepartureStatus.TIDAK_ADA_JADWAL, "diff_minutes": None}

    expected = schedule['expected_departure']
    tolerance = schedule.get('tolerance_minutes', 15)

    actual_minutes = actual_time.hour * 60 + actual_time.minute
    expected_minutes = expected.hour * 60 + expected.minute
    diff = actual_minutes - expected_minutes   # negatif = pulang cepat, positif = lembur

    if abs(diff) <= tolerance:
        status = DepartureStatus.TEPAT_WAKTU
    elif diff < 0:
        status = DepartureStatus.PULANG_CEPAT
    else:
        status = DepartureStatus.PULANG_LEMBUR

    return {"status": status, "diff_minutes": diff}


def process_vehicle_detection(plate_text: str, detection_time: datetime):
    """
    Dipanggil setiap kali kamera mendeteksi plat nomor.
    Otomatis menentukan apakah ini kedatangan atau kepulangan.
    """
    vehicle = db.get_vehicle(plate_text)
    today = detection_time.date()
    day_of_week = detection_time.weekday()

    # Cek apakah sudah ada record hari ini
    record = db.get_attendance(vehicle.id, today)
    schedule = db.get_schedule(vehicle.id, day_of_week)

    if not record or not record.arrival_time:
        # → Ini adalah KEDATANGAN
        evaluation = evaluate_arrival(detection_time, schedule)
        db.create_or_update_attendance(
            vehicle_id=vehicle.id,
            tanggal=today,
            day_of_week=day_of_week,
            arrival_time=detection_time,
            arrival_status=evaluation['status'].value,
            arrival_scheduled=schedule.get('expected_arrival') if schedule else None,
            arrival_diff_minutes=evaluation['diff_minutes'],
            status_hari='HADIR'
        )
    else:
        # → Ini adalah KEPULANGAN
        evaluation = evaluate_departure(detection_time, schedule)
        duration = int((detection_time - record.arrival_time).total_seconds() / 60)
        db.update_attendance_departure(
            record_id=record.id,
            departure_time=detection_time,
            departure_status=evaluation['status'].value,
            departure_scheduled=schedule.get('expected_departure') if schedule else None,
            departure_diff_minutes=evaluation['diff_minutes'],
            parking_duration_minutes=duration
        )
```

#### Tabel Status Ketepatan Waktu

**Status Kedatangan:**

| Status | Kondisi | Badge | Keterangan |
|---|---|---|---|
| `TEPAT_WAKTU` | Datang ≤ jadwal + toleransi | 🟢 Hijau | Datang tepat waktu |
| `TERLAMBAT` | Datang > jadwal + toleransi | 🔴 Merah | Datang terlambat |
| `TIDAK_ADA_JADWAL` | Tidak ada jadwal di hari tersebut | ⚪ Abu-abu | Tidak terjadwal (libur/off) |

**Status Kepulangan:**

| Status | Kondisi | Badge | Keterangan |
|---|---|---|---|
| `TEPAT_WAKTU` | Pulang ≈ jadwal (±toleransi) | 🟢 Hijau | Pulang sesuai jadwal |
| `PULANG_CEPAT` | Pulang < jadwal - toleransi | 🟡 Kuning | Pulang lebih awal |
| `PULANG_LEMBUR` | Pulang > jadwal + toleransi | 🔵 Biru | Pulang lebih lama (lembur) |
| `TIDAK_ADA_JADWAL` | Tidak ada jadwal di hari tersebut | ⚪ Abu-abu | Tidak terjadwal |

**Status Harian:**

| Status | Keterangan |
|---|---|
| `HADIR` | Terdeteksi masuk di hari tersebut |
| `BELUM_MASUK` | Hari kerja berjalan, belum terdeteksi masuk |
| `IZIN` | Ditandai manual oleh admin (izin) |
| `SAKIT` | Ditandai manual oleh admin (sakit) |
| `ALPA` | Tidak terdeteksi, tidak ada izin/sakit |

#### Layout UI — Dashboard Kehadiran

```
┌──────────────────────────────────────────────────────────────┐
│  📋 MONITORING KEHADIRAN KENDARAAN         [📅 Hari Ini] [🔽] │
├──────────────────────┬───────────────────────────────────────┤
│                      │                                       │
│  📊 Ringkasan Hari   │  📋 Daftar Kendaraan Terdaftar        │
│  ┌────────────────┐  │  ┌─────────────────────────────────┐  │
│  │ Hadir:     15  │  │  │ 🟢 B 1234 ABC | Dekan          │  │
│  │ Terlambat:  3  │  │  │    Masuk: 07:25 ✅ Tepat Waktu  │  │
│  │ P. Cepat:   1  │  │  │    Jadwal: 07:30 (tol. 15 mnt) │  │
│  │ Lembur:     2  │  │  │    Keluar: belum               │  │
│  │ Belum:      4  │  │  ├─────────────────────────────────┤  │
│  │ Izin/Sakit: 1  │  │  │ 🔴 D 5678 XYZ | Dosen          │  │
│  │ Alpa:       1  │  │  │    Masuk: 08:45 ❌ Terlambat    │  │
│  └────────────────┘  │  │    Jadwal: 08:00 (tol. 30 mnt) │  │
│                      │  │    Selisih: +45 menit           │  │
│  ⏰ Status Real-time │  │    Keluar: belum               │  │
│  ┌────────────────┐  │  ├─────────────────────────────────┤  │
│  │ 07:30 ──────── │  │  │ 🟡 B 9999 QRS | Wakil Dekan    │  │
│  │  │ De... ✅    │  │  │    Masuk: 07:40 ✅ Tepat Waktu  │  │
│  │  │ WD... ✅    │  │  │    Jadwal: 08:00 (tol. 15 mnt) │  │
│  │  │ DS... ❌    │  │  │    Keluar: 14:30 🟡 P. Cepat   │  │
│  │ 08:00 ──────── │  │  │    Jadwal: 16:00 (-90 mnt)     │  │
│  │ 08:45 ──────── │  │  ├─────────────────────────────────┤  │
│  │  ...           │  │  │ ⚪ B 4444 LMN | Dosen           │  │
│  └────────────────┘  │  │    Status: Belum Masuk ⏳      │  │
│                      │  │    Jadwal: 08:00 (tol. 30 mnt) │  │
│  📅 Filter:          │  └─────────────────────────────────┘  │
│  [Hari Ini ▼]        │                                       │
│  [Semua Status ▼]    │  📈 Grafik Ketepatan Waktu (Mingguan) │
│  [Semua Jabatan ▼]   │  ┌─────────────────────────────────┐  │
│                      │  │ [Bar chart: % tepat waktu per    │  │
│                      │  │  orang selama seminggu]          │  │
│                      │  └─────────────────────────────────┘  │
├──────────────────────┴───────────────────────────────────────┤
│  📱 Bottom Nav (Mobile): [Dashboard] [Slots] [Kehadiran] [Log]│
└──────────────────────────────────────────────────────────────┘
```

#### Halaman Konfigurasi Jadwal

Halaman terpisah untuk admin mengatur jadwal masuk/keluar per kendaraan per hari:

```
┌──────────────────────────────────────────────────────────────┐
│  ⚙️ KONFIGURASI JADWAL KENDARAAN                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  [🔍 Cari kendaraan...]   [+ Tambah Jadwal]                  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ B 1234 ABC — Prof. Ahmad (Dekan)                     │    │
│  │ ┌──────┬───────────┬───────────┬──────────┐          │    │
│  │ │ Hari │ Masuk     │ Keluar    │ Toleransi│          │    │
│  │ ├──────┼───────────┼───────────┼──────────┤          │    │
│  │ │ Senin│ 07:30     │ 16:00     │ 15 mnt   │  [✏️]   │    │
│  │ │ Selasa│ 07:30    │ 16:00     │ 15 mnt   │  [✏️]   │    │
│  │ │ Rabu │ 07:30     │ 16:00     │ 15 mnt   │  [✏️]   │    │
│  │ │ Kamis│ 07:30     │ 14:00     │ 15 mnt   │  [✏️]   │    │
│  │ │ Jumat│ 07:30     │ 11:30     │ 15 mnt   │  [✏️]   │    │
│  │ │ Sabtu│ —         │ —         │ —        │  [✏️]   │    │
│  │ │ Minggu│ —        │ —         │ —        │  [✏️]   │    │
│  │ └──────┴───────────┴───────────┴──────────┘          │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ D 5678 XYZ — Dr. Budi (Dosen)                        │    │
│  │ ┌──────┬───────────┬───────────┬──────────┐          │    │
│  │ │ Hari │ Masuk     │ Keluar    │ Toleransi│          │    │
│  │ ├──────┼───────────┼───────────┼──────────┤          │    │
│  │ │ Senin│ 08:00     │ 15:00     │ 30 mnt   │  [✏️]   │    │
│  │ │ ...  │ ...       │ ...       │ ...      │          │    │
│  │ └──────┴───────────┴───────────┴──────────┘          │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  📝 Tips: Jadwal yang kosong (—) berarti tidak terjadwal      │
│     di hari tersebut. Status otomatis = TIDAK_ADA_JADWAL.    │
└──────────────────────────────────────────────────────────────┘
```

#### Halaman Laporan Kehadiran (Rekap)

```
┌──────────────────────────────────────────────────────────────┐
│  📊 LAPORAN KEHADIRAN                  [📅 Jan 2025 ▼] [📥 Export]│
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Filter: [Bulan ▼] [Jabatan ▼] [Status ▼] [Export CSV/Excel]│
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ Rekap Bulanan — Januari 2025                         │    │
│  │                                                      │    │
│  │ No │ Plat      │ Nama       │ Jab.  │ H  T  PC L A │    │
│  │────┼───────────┼────────────┼───────┼───────────────│    │
│  │  1 │ B 1234 ABC│ Prof. Ahmad│ Dekan │ 20 0  0 2 0 │    │
│  │  2 │ D 5678 XYZ│ Dr. Budi   │ Dosen │ 18 3  1 0 0 │    │
│  │  3 │ B 9999 QRS│ Dr. Citra  │ W.Dek │ 19 1  0 1 1 │    │
│  │────┼───────────┼────────────┼───────┼───────────────│    │
│  │                    Total    │       │ 57 4  1 3 1 │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  Keterangan: H=Hadir  T=Terlambat  PC=Pulang Cepat          │
│             L=Lembur  A=Alpa                                 │
│                                                              │
│  📈 Statistik:                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ [Pie chart: distribusi status kedatangan]            │    │
│  │ [Line chart: tren ketepatan waktu mingguan]          │    │
│  │ [Bar chart: ranking keterlambatan per orang]         │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  📋 Detail per hari (klik nama untuk expand):                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ ▼ Dr. Budi — Januari 2025                            │    │
│  │  Tgl │ Masuk  │ Status     │ Keluar │ Status        │    │
│  │  02  │ 07:55  │ ✅ Tepat   │ 15:10  │ ✅ Tepat     │    │
│  │  03  │ 08:45  │ ❌ +45mnt  │ 15:05  │ ✅ Tepat     │    │
│  │  06  │ 07:50  │ ✅ Tepat   │ 14:20  │ 🟡 PC -40mnt │    │
│  │  ... │ ...    │ ...        │ ...    │ ...           │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

#### API Endpoint untuk Monitoring Kehadiran

```python
# REST — Rekap kehadiran harian
@router.get("/api/attendance/today")
async def get_today_attendance():
    """
    Return daftar semua kendaraan terdaftar + status kehadiran hari ini.
    Otomatis menghitung status berdasarkan jadwal.
    """
    ...

# REST — Rekap kehadiran bulanan (untuk laporan)
@router.get("/api/attendance/recap")
async def get_attendance_recap(
    month: int,
    year: int,
    jabatan: Optional[str] = None,
    vehicle_id: Optional[int] = None
):
    """
    Return rekap kehadiran bulanan: total hadir, terlambat, pulang cepat,
    lembur, alpa per kendaraan. Support export CSV.
    """
    ...

# REST — CRUD jadwal kendaraan
@router.get("/api/schedules")
async def get_schedules(vehicle_id: Optional[int] = None):
    ...

@router.post("/api/schedules")
async def create_schedule(schedule: VehicleScheduleCreate):
    ...

@router.put("/api/schedules/{id}")
async def update_schedule(id: int, schedule: VehicleScheduleUpdate):
    ...

@router.delete("/api/schedules/{id}")
async def delete_schedule(id: int):
    ...

# REST — Detail kehadiran per kendaraan (expandable)
@router.get("/api/attendance/{vehicle_id}/detail")
async def get_vehicle_attendance_detail(
    vehicle_id: int,
    month: int,
    year: int
):
    """
    Return detail kehadiran harian per kendaraan:
    jam masuk, jam keluar, status, selisih menit, gambar bukti.
    """
    ...

# REST — Statistik ketepatan waktu (untuk chart)
@router.get("/api/attendance/stats")
async def get_attendance_stats(
    period: str = "weekly",   # weekly / monthly
    jabatan: Optional[str] = None
):
    """
    Return statistik: % tepat waktu, tren keterlambatan,
    ranking kendaraan paling sering terlambat.
    """
    ...

# REST — Override status manual (izin/sakit/alpa)
@router.patch("/api/attendance/{id}/override")
async def override_attendance_status(id: int, status: str, note: str):
    """
    Admin bisa override status: IZIN, SAKIT, ALPA.
    Digunakan saat kendaraan tidak terdeteksi tapi ada keterangan.
    """
    ...

# REST — Export laporan (CSV / Excel)
@router.get("/api/attendance/export")
async def export_attendance_report(
    month: int,
    year: int,
    format: str = "csv"   # csv / xlsx
):
    ...
```

#### Komponen UI — Monitoring Kehadiran

| Komponen | Deskripsi | Mobile Support |
|---|---|---|
| Attendance Card | Kartu per kendaraan: plat, nama, status masuk/keluar, selisih waktu | ✅ Single column stack |
| Status Badge | Badge warna: hijau (tepat), merah (terlambat), kuning (pulang cepat), biru (lembur) | ✅ High contrast |
| Timeline View | Timeline vertikal: siapa masuk jam berapa, siapa sudah pulang | ✅ Scrollable vertical |
| Schedule Editor | Tabel jadwal per kendaraan per hari (inline edit) | ✅ Accordion per hari |
| Recap Table | Tabel rekap bulanan (Hadir, Terlambat, P.Cepat, Lembur, Alpa) | ✅ Horizontal scroll + sticky header |
| Chart Ketepatan Waktu | Pie/Bar/Line chart statistik kehadiran | ✅ Responsive chart (Chart.js) |
| Export Button | Download laporan CSV/Excel | ✅ Share sheet di mobile |
| Filter Bar | Filter berdasarkan tanggal, jabatan, status | ✅ Bottom sheet filter |
| Manual Override | Admin bisa override status (izin/sakit/alpa) | ✅ Bottom sheet form |
| Live Clock | Jam real-time di dashboard (referensi waktu sekarang) | ✅ Top bar clock |

### 6.6 Desain Responsif (Mobile-First)

#### Breakpoint & Layout Strategy

```css
/* Mobile-First Breakpoints */
:root {
    --bp-mobile:   320px;    /* Default — single column */
    --bp-tablet:   768px;    /* 2-column grid */
    --bp-desktop:  1024px;   /* Full dashboard layout */
    --bp-wide:     1440px;   /* Max-width container */
}

/* Mobile (< 768px) */
/* ────────────────────── */
/* - Single column layout */
/* - Bottom navigation bar (fixed) */
/* - Swipeable tabs untuk switch section */
/* - Card-based UI (bukan table) */
/* - Pull-to-refresh untuk reload data */
/* - Floating Action Button (FAB) untuk aksi cepat */
/* - Touch-optimized: min tap target 48x48px */
/* - Image cropper: pinch-to-zoom + gesture */
/* - Canvas editor: simplified polygon tool */

/* Tablet (768px - 1023px) */
/* ────────────────────── */
/* - 2-column grid */
/* - Side navigation (collapsible) */
/* - Table view + card toggle */

/* Desktop (≥ 1024px) */
/* ────────────────────── */
/* - Full dashboard layout (seperti wireframe di atas) */
/* - Side + top navigation */
/* - Multi-panel: peta slot + live feed + log */
```

#### Komponen Mobile-Specific

| Komponen Mobile | Fungsi | Pengganti Desktop |
|---|---|---|
| Bottom Nav Bar | Navigasi utama (Dashboard, Slots, Register, Log) | Side navigation |
| FAB (Floating Action Button) | Quick action: capture foto plat, add slot | Toolbar buttons |
| Swipeable Tabs | Switch antar sub-section | Tab bar / sidebar |
| Pull-to-Refresh | Reload data real-time | Refresh button |
| Bottom Sheet | Detail event / form metadata | Modal dialog |
| Card View | List kejadian (menggantikan table) | Data table |
| Notification Toast | Alert pelanggaran baru | Desktop notification |
| Haptic Feedback | Getar saat ada pelanggaran tinggi | Sound alert |
| Camera Capture | Gunakan kamera HP langsung | File upload |
| Touch Gesture | Pinch zoom, swipe, long-press | Mouse interactions |

#### PWA (Progressive Web App) Support

```json
{
  "name": "Sistem Parkir Cerdas",
  "short_name": "ParkirAI",
  "description": "Monitoring & pendaftaran sistem parkir cerdas berbasis ML",
  "start_url": "/dashboard",
  "display": "standalone",
  "theme_color": "#1E40AF",
  "background_color": "#F8FAFC",
  "orientation": "any",
  "icons": [
    {"src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
    {"src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png"}
  ],
  "features": [
    "camera_access",
    "push_notifications",
    "offline_caching",
    "background_sync"
  ]
}
```

**Fitur PWA:**
- **Offline Mode:** Dashboard tetap bisa dibuka (cached), data pendaftaran di-queue dan sync saat online
- **Push Notification:** Notifikasi pelanggaran parkir langsung ke HP admin
- **Camera Access:** Akses kamera HP langsung untuk capture plat nomor dan area parkir
- **Installable:** Bisa di-install ke home screen seperti aplikasi native
- **Background Sync:** Data yang diinput saat offline otomatis tersync saat koneksi kembali

### 6.7 Routing & Halaman Web UI

```
/                           → Redirect ke /dashboard
/login                      → Halaman login (JWT auth)
/dashboard                  → Dashboard monitoring utama
/dashboard/slots            → Peta visual slot parkir (real-time)
/dashboard/events           → Log semua kejadian (filter, search, pagination)
/dashboard/stats            → Statistik & chart (harian/mingguan/bulanan)
/dashboard/attendance       → Monitoring kehadiran & ketepatan waktu (real-time)
/dashboard/attendance/schedules → Konfigurasi jadwal kendaraan
/dashboard/attendance/recap → Laporan rekap kehadiran bulanan
/register/plate             → Form pendaftaran plat nomor (training ALPR)
/register/plate/batch       → Batch upload plat nomor (multi-file / zip)
/register/plate/history     → Riwayat plat yang sudah didaftarkan
/register/parking-area      → Canvas editor garis area parkir
/register/parking-area/history → Riwayat konfigurasi area parkir
/register/camera            → Kelola sumber kamera (tambah/edit/hapus)
/settings                   → Pengaturan sistem (threshold, MQTT, user)
/settings/users             → Manajemen user & role
/settings/mqtt              → Konfigurasi MQTT broker & ESP32
/captures/:id               → Detail capture (gambar + metadata + aksi)
```

### 6.7 Autentikasi & Role

```python
# Role-based access control
ROLES = {
    "admin": {
        "permissions": ["*"],                      # Full access
        "description": "Administrator sistem"
    },
    "operator": {
        "permissions": [
            "register:plate",                       # Daftarkan plat
            "register:parking_area",                # Daftarkan area parkir
            "monitor:view",                         # Lihat monitoring
            "monitor:resolve_event"                 # Resolve event
        ],
        "description": "Operator parkir"
    },
    "viewer": {
        "permissions": [
            "monitor:view"                          # Hanya lihat monitoring
        ],
        "description": "Pengawas / tamu"
    }
}
```

---

## 7. Arsitektur Sistem Terintegrasi

```
┌─────────────────────────────────────────────────────────────────┐
│                        SISTEM PARKIR CERDAS                     │
├──────────────┬──────────────────┬────────────────┬──────────────┤
│  LAYER INPUT │   LAYER PROSES   │  LAYER LOGIKA  │ LAYER OUTPUT │
├──────────────┼──────────────────┼────────────────┼──────────────┤
│              │                  │                │              │
│  Kamera      │  ALPR / YOLOv8   │  K-Map Logic   │  LED Status  │
│  IP/CCTV ───►│  + PaddleOCR  ──►│  M = D + W  ──►│  (Hijau/     │
│              │                  │  O = D+W+S     │   Merah)     │
│              │  Validasi DB ───►│                │              │
│  Kamera      │  (SQLite/        │  Slot          │  Buzzer      │
│  Top-down ──►│   PostgreSQL)    │  Validation ──►│              │
│              │                  │                │  OLED Display│
│  Sensor PIR  │  CNN Slot        │  MQTT Publish ►│              │
│  (opsional)──│  Detector     ──►│                │  Dashboard   │
│              │  (MobileNetV3)   │                │  Web         │
└──────────────┴──────────────────┴────────────────┴──────────────┘
                        ▲                  ▲
                        │                  │
                  [FastAPI Server]   [ESP32 via MQTT]
```

### 7.1 Komponen Server ML

- **Framework:** FastAPI (Python)
- **ML Runtime:** PyTorch / ONNX Runtime (inference)
- **Database:** SQLite (dev) / PostgreSQL (production)
- **Message Broker:** MQTT (Mosquitto)
- **Dashboard:** Next.js (React) + Tailwind CSS
- **Real-time:** WebSocket (FastAPI) + Server-Sent Events

---

## 8. Stack Teknologi

### Computer Vision & ML

| Komponen | Teknologi |
|---|---|
| Object Detection | YOLOv8 (Ultralytics) |
| OCR | PaddleOCR / EasyOCR |
| Slot Classification | MobileNetV3 / EfficientNet-Lite |
| Image Processing | OpenCV 4.x |
| Deep Learning | PyTorch 2.x |
| Inference Optimization | ONNX Runtime |

### Backend & Database

| Komponen | Teknologi |
|---|---|
| API Server | FastAPI (Python 3.11+) |
| Database | PostgreSQL + SQLAlchemy |
| Message Broker | Mosquitto MQTT |
| Cache | Redis |
| Container | Docker + Docker Compose |

### IoT & Embedded

| Komponen | Teknologi |
|---|---|
| Mikrokontroler | ESP32 DevKit V1 |
| Firmware | Arduino IDE / PlatformIO |
| Protokol | MQTT over WiFi |
| Library | PubSubClient, ArduinoJson |

### Frontend & Web UI

| Komponen | Teknologi |
|---|---|
| Framework | Next.js 14 (React) |
| Styling | Tailwind CSS + shadcn/ui |
| State Management | Zustand + React Query |
| Real-time | WebSocket (native) + reconnecting-websocket |
| Canvas Editor | Fabric.js / Konva.js (polygon drawing) |
| Image Cropper | react-image-crop + pinch-zoom |
| Charts | Recharts / Chart.js |
| PWA | next-pwa (Workbox) |
| Mobile Optimization | Responsive design + PWA installable |
| Auth | NextAuth.js (JWT + session) |
| Push Notification | Web Push API + Firebase Cloud Messaging |

### Monitoring & Logging

| Komponen | Teknologi |
|---|---|
| Logging | Python logging + ELK Stack |
| Visualisasi | Chart.js / Plotly |
| Error Tracking | Sentry |

---

## 9. Rencana Implementasi & Timeline

### Fase 1 — Setup & Data (Minggu 1–2)

- [ ] Setup lingkungan pengembangan (Python, Docker, Arduino IDE)
- [ ] Setup Next.js project dengan Tailwind CSS
- [ ] Pengumpulan dataset plat nomor Indonesia
- [ ] Pengumpulan dataset gambar slot parkir (kosong/terisi)
- [ ] Perancangan skema database kendaraan & anotasi
- [ ] Setup MQTT Broker (Mosquitto)

### Fase 2 — Development ML (Minggu 3–5)

- [ ] Training model YOLOv8 untuk deteksi plat nomor
- [ ] Integrasi dan fine-tuning PaddleOCR
- [ ] Evaluasi akurasi pipeline ALPR (target: ≥ 85% end-to-end accuracy)
- [ ] Training CNN klasifikasi slot parkir
- [ ] Pengujian unit setiap modul ML

### Fase 3 — Development Backend & Logika (Minggu 6–7)

- [ ] Implementasi FastAPI server
- [ ] Implementasi fungsi `compute_cluster()` berdasarkan K-Map
- [ ] Implementasi `validate_parking_position()`
- [ ] Integrasi semua modul ML ke API endpoint
- [ ] Unit testing logika K-Map dengan semua kombinasi input

### Fase 6 — Development Web UI (Minggu 8–12)

- [ ] Setup Next.js project structure (pages, components, hooks, stores)
- [ ] Implement authentication system (login, JWT, role-based access)
- [ ] Build halaman pendaftaran plat nomor (upload, crop, metadata form)
- [ ] Build canvas editor untuk garis area parkir (polygon tool, snap-to-edge)
- [ ] Implement batch upload plat nomor (multi-file + zip support)
- [ ] Build dashboard monitoring real-time (WebSocket, live feed, peta slot)
- [ ] Implement log kejadian dengan filter & pagination
- [ ] Build fitur monitoring kehadiran & ketepatan waktu (attendance tracking)
- [ ] Implement konfigurasi jadwal kendaraan (schedule management)
- [ ] Build laporan rekap kehadiran bulanan (recap & export CSV/Excel)
- [ ] Build responsive design (mobile-first, bottom nav, FAB, swipeable tabs)
- [ ] Implement PWA (manifest, service worker, offline mode, push notification)
- [ ] Implement camera capture integration (mobile browser camera API)
- [ ] Unit testing komponen Web UI

### Fase 7 — Development IoT ESP32 (Minggu 12–13)

- [ ] Perancangan dan perakitan hardware ESP32
- [ ] Penulisan firmware Arduino (MQTT subscribe + buzzer control)
- [ ] Pengujian koneksi WiFi dan MQTT
- [ ] Pengujian pola buzzer untuk setiap kondisi

### Fase 8 — Integrasi & Pengujian Sistem (Minggu 14–15)

- [ ] Integrasi end-to-end: Kamera → ML Server → MQTT → ESP32
- [ ] Integrasi Web UI ↔ FastAPI ↔ Database (plate registration, parking area, monitoring)
- [ ] Pengujian skenario lengkap (semua kombinasi jabatan dan kondisi)
- [ ] Pengujian Web UI di berbagai device (mobile, tablet, desktop)
- [ ] Pengujian PWA offline mode & push notification
- [ ] Pengujian stress (banyak kendaraan serentak)
- [ ] Debugging dan optimasi performa
- [ ] Kalibrasi ambang batas (confidence threshold)
- [ ] Usability testing Web UI dengan operator

### Fase 9 — Deployment & Dokumentasi (Minggu 16)

- [ ] Deployment server menggunakan Docker Compose
- [ ] Setup monitoring & alerting
- [ ] Deployment Web UI (Vercel / self-hosted via Docker)
- [ ] Penulisan dokumentasi teknis
- [ ] Panduan instalasi dan konfigurasi
- [ ] Panduan penggunaan Web UI untuk operator (mobile & desktop)
- [ ] Demo dan serah terima sistem

---

## 10. Struktur Direktori Proyek

```
smart-parking-system/
│
├── 📁 ml/                          # Modul Machine Learning
│   ├── alpr/                       # Automatic License Plate Recognition
│   │   ├── detector.py             # YOLOv8 plat detector
│   │   ├── ocr.py                  # PaddleOCR wrapper
│   │   ├── preprocessor.py         # Image preprocessing
│   │   └── pipeline.py             # End-to-end ALPR pipeline
│   │
│   ├── slot_detection/             # Deteksi slot parkir
│   │   ├── segmenter.py            # Hough Line Transform untuk garis parkir
│   │   ├── classifier.py           # CNN slot classifier (kosong/terisi)
│   │   └── validator.py            # Validasi posisi kendaraan
│   │
│   ├── models/                     # Model weights (.pt, .onnx)
│   │   ├── yolov8_plate.pt
│   │   └── slot_classifier.onnx
│   │
│   └── training/                   # Script training
│       ├── train_alpr.py
│       ├── train_slot.py
│       └── evaluate.py
│
├── 📁 logic/                       # Logika Karnaugh Map
│   ├── karnaugh.py                 # Implementasi M=D+W, O=D+W+S
│   └── cluster_validator.py        # Validasi hak akses cluster
│
├── 📁 api/                         # Backend FastAPI
│   ├── main.py                     # Entry point FastAPI
│   ├── routes/
│   │   ├── vehicle.py              # Endpoint validasi kendaraan
│   │   ├── parking.py              # Endpoint status slot
│   │   ├── notification.py         # Endpoint trigger notifikasi
│   │   ├── dataset.py              # Endpoint upload dataset training
│   │   ├── events.py               # Endpoint log kejadian (WebSocket + REST)
│   │   ├── attendance.py           # Endpoint monitoring kehadiran (today/recap/detail/export)
│   │   └── schedules.py            # CRUD jadwal kendaraan
│   ├── models/                     # SQLAlchemy models
│   │   ├── vehicle.py
│   │   ├── parking_log.py
│   │   ├── plate_annotation.py     # Model anotasi plat training
│   │   ├── slot_annotation.py      # Model anotasi slot training
│   │   ├── parking_event.py        # Model log kejadian
│   │   ├── vehicle_schedule.py     # Model jadwal kendaraan (per hari)
│   │   └── attendance_log.py       # Model log kehadiran (masuk/keluar)
│   ├── services/                   # Business logic services
│   │   ├── attendance_service.py   # Logika evaluasi ketepatan waktu (arrival/departure)
│   │   └── export_service.py       # Export laporan CSV/Excel
│   ├── database.py                 # Database connection
│   ├── config.py                   # Konfigurasi aplikasi
│   ├── mqtt_client.py              # MQTT publisher
│   └── event_bus.py                # Event bus untuk WebSocket broadcast
│
├── 📁 web/                         # Frontend Next.js (Web UI)
│   ├── app/                        # Next.js 14 App Router
│   │   ├── (auth)/
│   │   │   └── login/
│   │   │       └── page.tsx        # Halaman login
│   │   ├── (dashboard)/
│   │   │   ├── page.tsx            # Dashboard monitoring utama
│   │   │   ├── slots/
│   │   │   │   └── page.tsx        # Peta slot real-time
│   │   │   ├── events/
│   │   │   │   └── page.tsx        # Log kejadian & pelanggaran
│   │   │   ├── stats/
│   │   │   │   └── page.tsx        # Statistik & chart
│   │   │   ├── attendance/
│   │   │   │   ├── page.tsx                 # Monitoring kehadiran real-time
│   │   │   │   ├── schedules/
│   │   │   │   │   └── page.tsx             # Konfigurasi jadwal kendaraan
│   │   │   │   └── recap/
│   │   │   │       └── page.tsx             # Laporan rekap bulanan
│   │   │   ├── register/
│   │   │   │   ├── plate/
│   │   │   │   │   ├── page.tsx             # Form pendaftaran plat
│   │   │   │   │   ├── batch/
│   │   │   │   │   │   └── page.tsx         # Batch upload plat
│   │   │   │   │   └── history/
│   │   │   │   │       └── page.tsx         # Riwayat pendaftaran plat
│   │   │   │   ├── parking-area/
│   │   │   │   │   ├── page.tsx             # Canvas editor area parkir
│   │   │   │   │   └── history/
│   │   │   │   │       └── page.tsx         # Riwayat konfigurasi area
│   │   │   │   └── camera/
│   │   │   │       └── page.tsx             # Kelola sumber kamera
│   │   │   └── settings/
│   │   │       ├── page.tsx                 # Pengaturan sistem
│   │   │       ├── users/
│   │   │       │   └── page.tsx             # Manajemen user
│   │   │       └── mqtt/
│   │   │           └── page.tsx             # Konfigurasi MQTT
│   │   ├── layout.tsx              # Root layout + providers
│   │   └── globals.css             # Global styles (Tailwind)
│   │
│   ├── components/                 # Reusable UI components
│   │   ├── ui/                     # shadcn/ui components
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── input.tsx
│   │   │   └── ...
│   │   ├── dashboard/
│   │   │   ├── slot-map.tsx                 # Peta visual slot (SVG/Canvas)
│   │   │   ├── live-feed.tsx                # Live CCTV feed player
│   │   │   ├── event-log.tsx                # Log kejadian real-time
│   │   │   ├── stats-card.tsx               # Card statistik
│   │   │   └── hourly-chart.tsx             # Chart kendaraan per jam
│   │   ├── attendance/
│   │   │   ├── attendance-card.tsx          # Kartu status kehadiran per kendaraan
│   │   │   ├── status-badge.tsx             # Badge status (tepat/terlambat/p. cepat/lembur)
│   │   │   ├── timeline-view.tsx            # Timeline vertikal kedatangan
│   │   │   ├── schedule-editor.tsx          # Editor jadwal per kendaraan per hari
│   │   │   ├── recap-table.tsx              # Tabel rekap bulanan
│   │   │   ├── punctuality-chart.tsx        # Chart ketepatan waktu (pie/bar/line)
│   │   │   └── attendance-filter.tsx        # Filter tanggal/status/jabatan
│   │   ├── register/
│   │   │   ├── plate-upload.tsx             # Upload & crop plat
│   │   │   ├── plate-metadata-form.tsx      # Form metadata plat
│   │   │   ├── parking-canvas.tsx           # Canvas editor polygon
│   │   │   ├── slot-labeler.tsx             # Label slot (ID + cluster)
│   │   │   └── batch-uploader.tsx           # Multi-file upload
│   │   ├── mobile/
│   │   │   ├── bottom-nav.tsx               # Bottom navigation bar
│   │   │   ├── fab.tsx                      # Floating Action Button
│   │   │   ├── swipeable-tabs.tsx           # Swipeable tab container
│   │   │   └── pull-to-refresh.tsx          # Pull-to-refresh wrapper
│   │   └── layout/
│   │       ├── sidebar.tsx                  # Desktop sidebar navigation
│   │       ├── header.tsx                   # Top header
│   │       └── responsive-container.tsx     # Responsive wrapper
│   │
│   ├── hooks/                      # Custom React hooks
│   │   ├── use-websocket.ts        # WebSocket connection hook
│   │   ├── use-camera.ts           # Camera capture hook
│   │   ├── use-offline.ts          # Offline detection hook
│   │   └── use-pull-refresh.ts     # Pull-to-refresh hook
│   │
│   ├── stores/                     # Zustand state management
│   │   ├── auth-store.ts           # Auth state (user, token)
│   │   ├── event-store.ts          # Event log state
│   │   └── slot-store.ts           # Slot status state
│   │
│   ├── lib/                        # Utility functions
│   │   ├── api.ts                  # API client (fetch wrapper)
│   │   ├── auth.ts                 # Auth helpers (JWT, session)
│   │   ├── utils.ts                # General utilities
│   │   └── constants.ts            # App constants
│   │
│   ├── public/                     # Static assets
│   │   ├── manifest.json           # PWA manifest
│   │   ├── sw.js                   # Service worker
│   │   └── icons/                  # PWA icons (192x192, 512x512)
│   │
│   ├── next.config.js              # Next.js config
│   ├── tailwind.config.js          # Tailwind CSS config
│   ├── tsconfig.json               # TypeScript config
│   └── package.json                # Dependencies
│
├── 📁 iot/                         # Firmware ESP32
│   ├── esp32_parking/
│   │   ├── esp32_parking.ino       # Main Arduino sketch
│   │   ├── buzzer.h                # Buzzer patterns
│   │   ├── mqtt_handler.h          # MQTT subscribe/publish
│   │   ├── display.h               # OLED display
│   │   └── config.h                # WiFi & MQTT config
│   └── wiring_diagram/
│       └── esp32_schematic.pdf
│
├── 📁 data/                        # Dataset & konfigurasi
│   ├── vehicles_db.sql             # Seed data kendaraan
│   ├── slot_config.json            # Konfigurasi slot parkir
│   └── training_dataset/           # Dataset untuk training
│       ├── plates/                 # Gambar plat nomor
│       └── slots/                  # Gambar slot parkir
│
├── 📁 docs/                        # Dokumentasi
│   ├── Karnaugh_Map_Parkir.docx
│   ├── arsitektur_sistem.png
│   ├── API_reference.md
│   └── web_ui_guide.md             # Panduan penggunaan Web UI
│
├── 📁 tests/                       # Unit tests
│   ├── test_karnaugh.py
│   ├── test_alpr.py
│   ├── test_slot.py
│   └── test_api.py
│
├── docker-compose.yml              # Orkestrasi container
├── requirements.txt                # Python dependencies (backend)
└── README.md                       # Petunjuk instalasi
```

---

## Catatan Penting

**Integritas Logika K-Map:** Persamaan `M = D + W` dan `O = D + W + S` harus diimplementasikan sebagai fungsi murni (pure function) yang menjadi *single source of truth* untuk penentuan hak akses cluster. Tidak boleh ada logika penentuan cluster di tempat lain selain modul `logic/karnaugh.py`.

**Prioritas Cluster Merah:** Kendaraan ber-jabatan Dekan (D) atau Wakil Dekan (W) secara otomatis juga memenuhi syarat Cluster Orange (O), namun sistem harus memprioritaskan mereka ke Cluster Merah terlebih dahulu.

**Failsafe IoT:** Jika koneksi MQTT terputus, ESP32 harus membunyikan **buzzer alarm khusus** (fail-safe) untuk memberitahu operator bahwa koneksi server terputus. LED merah tetap menyala sebagai indikator visual.

---

*Dokumen ini merupakan rencana pengembangan teknis dan dapat direvisi sesuai kebutuhan lapangan.*
