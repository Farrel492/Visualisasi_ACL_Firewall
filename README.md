# Firewall Simulator

Simulator firewall jaringan virtual berbasis web (Streamlit). Pengguna merancang topologi (PC, switch, router firewall, server), menyusun aturan filter paket, mengirim paket uji, lalu melihat **keputusan firewall (ACCEPT, DROP, NO_ROUTE) beserta alasannya** di topologi 2D, replay 3D, log, dan peringatan. Semuanya simulasi: tidak ada paket atau perangkat jaringan nyata yang disentuh.

## Menjalankan

Persyaratan: Python 3.13 (diuji), dependensi di `requirements.txt` (Streamlit 1.66.1, Plotly, pytest).

```
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Buka `http://localhost:8501`, lalu klik **Muat demo siap pakai** di halaman Mulai di Sini.

Matikan terjemahan otomatis browser (Chrome/Edge Translate) untuk `localhost`; terjemahan merusak label dan dapat memicu error tampilan.

## Menguji

```
.\.venv\Scripts\python.exe -m pytest -q
```

Ringkasan hasil dan pemetaan T01-T14 ada di `docs/TEST_REPORT.md`.

## Fitur

- **Topologi 2D** interaktif: gambar perangkat, seret untuk memindahkan, kabel FastEthernet/Serial, switch 24 port.
- **Visualisasi 3D** (Three.js, dibundel lokal): putar, zoom, geser, replay paket langkah demi langkah; DROP berhenti di router.
- **Aturan firewall** berurutan (first match wins), default policy per chain, Naik/Turun/Aktifkan/Hapus.
- **Simulasi paket**: uji cepat dan paket kustom, kartu hasil dengan alasan dan jalur.
- **Log trafik** dan **pusat peringatan** (DROP bukan otomatis serangan).
- **Lab belajar**: skenario terpandu dengan penilaian Lulus/Belum sesuai.
- **Konsol CLI** gaya Cisco IOS (router, switch) dan Windows (PC, server).
- **Penyimpanan otomatis**: pekerjaan tetap ada setelah refresh (token di URL `?w=...`).
- Proyek dapat diekspor dan diimpor (JSON) dari Dasbor.

## Struktur

```
app.py                      kerangka aplikasi dan router halaman
src/firewall_sim/core/      engine: model, aturan, simulator, validasi, alert, analitik
src/firewall_sim/config/    ConfigService, parser CLI lama, CLI gaya Cisco (ios_cli.py)
src/firewall_sim/storage/   simpan/muat proyek (JSON)
src/firewall_sim/scenarios/ topologi demo dan skenario Lab
src/firewall_sim/ui/        halaman, komponen, tema, workspace, komponen 2D/3D (frontend/)
static/fonts/               IBM Plex (lisensi OFL)
tests/                      pytest
docs/                       PRD, panduan pengguna, laporan uji, changelog, ADR
```

## Dokumen

`docs/USER_GUIDE.md` (panduan), `docs/TEST_REPORT.md` (hasil uji), `docs/PROJECT_CONTEXT.md` (konteks teknis), `docs/CHANGELOG.md`, `docs/adr/` (keputusan arsitektur).

## Batasan

Router tunggal; ping yang berasal dari router sendiri (chain OUTPUT) belum didukung; tidak ada deteksi serangan otomatis (backlog P2). Lihat `docs/PROJECT_CONTEXT.md`.
