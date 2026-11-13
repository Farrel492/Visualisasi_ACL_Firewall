# CHANGELOG

Format tiap entri: Date; version; Added/Changed/Fixed; impacted modules; tests performed; known limitations; next steps.

## [Unreleased]

### 2026-11-12: Rilis final (MVP lengkap)
- **Added:** Topologi 2D interaktif (gambar perangkat, seret, kabel Fa/Se, switch 24 port); visualisasi 3D Three.js; penyimpanan otomatis (token URL); rail navigasi tetap; Konsol CLI gaya Cisco/Windows (`config/ios_cli.py`); ekspor/impor proyek; peringatan dapat ditandai ditinjau; Lab Belajar dengan penilaian Lulus.
- **Changed:** halaman Dasbor, Konfigurasi Perangkat, Aturan Firewall, Simulasi Paket, Log Trafik, Pusat Peringatan, dan Lab Belajar ditulis ulang; tema "meja lab jaringan" (ADR-003); label dan teks tanpa ID internal.
- **Fixed:** Dasbor error setelah perubahan konfigurasi; Naik/Turun rule kini menukar urutan dengan benar; pilihan perangkat di Topologi 2D tidak tertimpa; tombol demo dapat dijangkau; tombol replay 3D berfungsi; data tidak hilang saat refresh.
- **Removed:** Mode Belajar/Profesional (keputusan produk); tes T11 diganti.
- **Tests:** 134 lulus (lihat `docs/TEST_REPORT.md`).
- **Known limitations:** ping dari router (chain OUTPUT) belum didukung; router tunggal.

### 2026-11-01: Fase 2a - Strip Status Dasbor, Tabel Uji Terbaru, Perbaikan Default Policy
- **Changed:**
  - `overview.py`: Empat kartu KPI besar (`st.metric`) diganti strip status satu baris (`st.html`) yang menampilkan revisi, jumlah perangkat, rule, link, dan status validasi secara ringkas.
  - `overview.py`: Blok 4-metrik aktivitas uji diganti tabel 5 entri terbaru (`st.dataframe`) dengan kolom Waktu, Sumber, Tujuan, Protokol, dan Keputusan.
  - `overview.py`: Default policy per chain menggunakan badge HTML dengan teks chain penuh dan warna ACCEPT/DROP dari token `theme.py`.
- **Added:**
  - 5 tes baru di `tests/test_acceptance.py`: `test_2a_compute_strip_data_default_lab`, `test_2a_compute_strip_data_valid_true_for_default_lab`, `test_2a_decision_color_returns_correct_colors`, `test_2a_decision_label_mapping_complete`, `test_2a_overview_module_importable`.
- **Impacted modules:** `ui/pages/overview.py`, `tests/test_acceptance.py`.
- **Tests performed (agen):** 72 passed in 7.83s (gerbang non-UI). Pytest penuh dijalankan oleh pengguna.
- **Next steps:** Sub-tahap 2b.

### 2026-11-01: Fase 1 - Perbaikan Bug Nyata, Dialog Konfirmasi, dan Manajemen Proyek
- **Added:**
  - B3: Dialog konfirmasi modal (`st.dialog`) untuk aksi destruktif: "Hapus riwayat uji" (`packet_sim.py`), "Kosongkan log" (`traffic_logs.py`), "Kosongkan peringatan" (`alerts.py`), dan "Bersihkan layar" (`cli_console.py`), memanfaatkan helper fungsi `clear_*` di `ui/state.py`.
  - B5: Manajemen proyek di Dasbor (`overview.py`) meliputi tombol "Proyek baru" (dialog konfirmasi modal memanggil `new_workspace()`), tombol "Ekspor proyek (JSON)", dan expander "Impor proyek".
  - Tes unit penerimaan baru: `test_T11_page_navigation_does_not_mutate_project_state` (pengganti T11), `test_B1_learning_lab_scenario_load`, `test_B3_clear_state_functions_isolation`, `test_B5_workspace_new_and_project_export_import` di `tests/test_acceptance.py`, serta `test_all_quick_commands_in_cli_console_are_valid` di `tests/test_cli_parser.py`.
- **Changed:**
  - B1: Tombol "Muat ke Workspace" di `learning_lab.py` kini memuat skenario, memindahkan halaman navigasi ke `network`, dan menampilkan notifikasi toast.
  - B2: Sintaks perintah `test` pada chip cepat dan panduan `cli_console.py` diperbaiki dari format lama `source=...` menjadi urutan parameter valid `test <src> <dst> <proto> [port]` yang 100% cocok dengan parser CLI.
  - B6: Dokumentasi README.md dan FAQ di `docs/USER_GUIDE.md` diperbarui dengan peringatan tegas menonaktifkan Chrome/Edge Translate untuk alamat localhost guna mencegah distorsi kata kunci dan error runtime DOM `removeChild`.
  - `docs/UI_AUDIT.md`: Diperbarui dengan hasil audit fungsionalitas dan formulir Fase 1 pada seluruh halaman.
- **Impacted modules:** `ui/pages/learning_lab.py`, `ui/pages/cli_console.py`, `ui/pages/packet_sim.py`, `ui/pages/traffic_logs.py`, `ui/pages/alerts.py`, `ui/pages/overview.py`, `README.md`, `docs/USER_GUIDE.md`, `docs/UI_AUDIT.md`, `tests/test_cli_parser.py`, `tests/test_acceptance.py`.
- **Tests performed:** 67 passed in 3.55s pada gerbang tes non-UI (`pytest -q --ignore=tests/test_ui.py --ignore=tests/test_benchmark.py --ignore=tests/test_workspace.py`).
- **Next steps:** Fase 2 - Penyesuaian tampilan halaman sesuai brief visual meja lab jaringan (2D/3D embed, listing mono, mini-topologi).

