# Konteks Proyek

## Tujuan
Simulator firewall jaringan virtual (Streamlit) untuk memahami evaluasi aturan filter paket: topologi, aturan, uji paket, keputusan, dan visualisasi. Tenggat pengumpulan tugas: 14 November 2026.

## Status (12 November 2026)
Semua fitur MVP selesai dan teruji: **134 tes lulus**. Halaman: Mulai di Sini, Dasbor, Topologi 2D, Konfigurasi Perangkat, Aturan Firewall, Simulasi Paket, Visualisasi 3D, Log Trafik, Pusat Peringatan, Lab Belajar, Konsol CLI. Fitur tambahan: penyimpanan otomatis, ekspor/impor proyek, CLI gaya Cisco.

## Arsitektur
```
core/       engine murni: models, rules, simulator, validation, alerts, analytics
config/     ConfigService (update_config), cli_parser (CLI lama), ios_cli (CLI gaya Cisco, murni)
storage/    json_store (ProjectState <-> JSON)
scenarios/  presets (default_lab: switch 24 port, router Fa0/0 Fa0/1 Se0/0 Se0/1) dan skenario Lab
ui/         app shell (shell.py), halaman (pages/), state.py, workspace.py, topo.py,
            theme.py, labels.py, widgets.py, frontend/ (komponen 2D SVG dan 3D Three.js)
```
Aturan utama: semua mutasi ProjectState lewat `apply_command` (ConfigService); UI tidak mengubah state langsung. Engine (`core/`) tidak bergantung pada Streamlit.

## Alur data
1. URL `?w=<token>` menentukan workspace. `init_session_state()` memuat `data/workspaces/<token>.json` bila ada.
2. Halaman memanggil `apply_command(...)`; revisi konfigurasi naik.
3. Di akhir tiap run, `persist_workspace()` menyimpan snapshot bila berubah (topologi, aturan, riwayat uji, log, peringatan, tata letak, kabel, riwayat CLI).
4. Komponen 2D/3D menerima payload dari `topo.component_payload(...)` dan mengirim event `layout` atau `select` yang diproses sekali per `nonce`.

## Keputusan
- Mode Belajar/Profesional dihapus (produk): tidak berfungsi dan membingungkan; tes T11 diganti.
- Three.js 0.160.1 dibundel lokal (`ui/frontend/scene3d/vendor/`, MIT), tanpa CDN; lihat ADR-002.
- Tampilan "meja lab jaringan": area kerja terang, layar instrumen gelap; font IBM Plex (OFL) lokal; lihat ADR-003.
- Router tunggal dan chain OUTPUT di luar MVP.

## Catatan pengembangan
- AppTest tidak dapat berjalan di terminal sandbox agen (soket diblokir); jalankan pytest penuh di terminal biasa.
- Sebagian halaman ditulis ulang dan diverifikasi lewat pytest dan render browser headless.
- Matikan terjemahan otomatis browser saat menguji.
- `data/` (workspace pengguna) dan `tmp_review/` diabaikan git.

## Backlog P2
Deteksi serangan berbasis korelasi, chain OUTPUT (ping dari router), NAT dan stateful, multi-router, ekspor laporan, Tab-completion CLI.
