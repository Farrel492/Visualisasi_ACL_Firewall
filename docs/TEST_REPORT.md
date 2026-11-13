# Laporan Pengujian

Hasil terakhir: **134 tes lulus, 0 gagal** (`.\.venv\Scripts\python.exe -m pytest -q`, Python 3.13, Streamlit 1.66.1).

## Pemetaan T01-T14 (PRD bagian 12)

| ID | Skenario PRD | Nama tes | Status |
|---|---|---|---|
| T01 | PC A ke server cocok ACCEPT | `test_T01_packet_accept_matched_rule` | Lulus |
| T02 | PC B ke server cocok DROP, event dan log muncul | `test_T02_packet_drop_generates_alert_and_log` | Lulus |
| T03 | Dua rule cocok berurutan, rule pertama menang | `test_T03_first_matching_terminal_action_wins` | Lulus |
| T04 | Rule disabled diabaikan | `test_T04_disabled_rule_is_ignored` | Lulus |
| T05 | IP perangkat diubah, uji berikutnya memakai IP baru | `test_T05_device_ip_change_applied_to_subsequent_tests` | Lulus |
| T06 | CLI menambah rule, GUI membaca rule yang sama | `test_T06_cli_added_rule_reflected_in_state` | Lulus |
| T07 | GUI mengubah rule, CLI `show` memakai nilai baru | `test_T07_gui_modified_rule_reflected_in_cli_show` | Lulus |
| T08 | Paket tanpa jalur menghasilkan NO_ROUTE | `test_T08_unroutable_packet_returns_no_route` | Lulus |
| T09 | IP/prefix tidak valid ditolak, state utuh | `test_T09_invalid_ip_prefix_rejected_state_preserved` | Lulus |
| T10 | DROP berhenti di firewall pada replay 3D | `test_T10_drop_packet_stops_at_firewall_in_3d_replay` | Lulus |
| T11 | (PRD: pergantian Learning/Professional) | `test_T11_page_navigation_does_not_mutate_project_state` | Lulus, lihat catatan |
| T12 | Event DROP normal tidak diberi label serangan | `test_T12_normal_drop_event_is_not_labeled_attack` | Lulus |
| T13 | Hasil lama menyimpan `config_revision` | `test_T13_historical_results_preserve_config_revision` | Lulus |
| T14 | Perintah CLI tidak dikenal, error aman tanpa shell | `test_T14_unknown_cli_command_safe_error_no_subprocess` | Lulus |

**Catatan T11:** fitur Mode Belajar/Profesional dihentikan atas keputusan produk (tidak berfungsi dan membingungkan pengguna). Tes T11 diganti dengan kriteria setara: berpindah halaman dan memuat demo tidak mengubah ProjectState selain lewat `apply_command`. PRD tidak diubah.

## Jumlah tes per berkas

| Berkas | Jumlah | Cakupan |
|---|---|---|
| `test_acceptance.py` | 22 | T01-T14 dan kasus pendukung |
| `test_engine.py` | 19 | Engine simulator, aturan, validasi |
| `test_ios_cli.py` | 16 | CLI gaya Cisco/Windows (murni) |
| `test_pages_2b.py` | 14 | Aturan Firewall, Konfigurasi Perangkat, Simulasi Paket |
| `test_ui.py` | 13 | Navigasi, halaman awal, demo, mode peringatan |
| `test_pages_2d.py` | 8 | Log Trafik, Pusat Peringatan, Lab Belajar, 3D |
| `test_cli_parser.py` | 7 | Parser CLI lama |
| `test_config_service.py` | 6 | ConfigService |
| `test_pages_cli.py` | 6 | Halaman Konsol CLI |
| `test_scenarios.py` | 5 | Skenario Lab |
| `test_workspace.py` | 5 | Penyimpanan otomatis, pemulihan setelah refresh |
| `test_analytics.py` | 4 | Statistik dan filter log |
| `test_storage.py`, `test_viz3d.py` | 3 + 3 | Simpan/muat proyek, frame replay |
| `test_smoke.py` | 2 | Impor dasar |
| `test_benchmark.py` | 1 | Benchmark |

## Benchmark

Topologi 10 perangkat dan 50 aturan, diukur di mesin pengembangan Windows (angka bergantung perangkat keras):

| Pengukuran | Hasil |
|---|---|
| `simulate_packet` (50 iterasi) | sekitar 0,64 ms per paket |
| Render halaman utama via AppTest | sekitar 0,92 detik |

## Verifikasi tampilan

Komponen 2D dan 3D diuji secara visual di browser headless (render, seret perangkat dengan nilai kembali ke Python, replay paket, DROP berhenti di router) dan oleh pengguna di browser. AppTest tidak dapat menguji isi WebGL; render 3D diverifikasi manual.

## Keterbatasan

- Ping yang berasal dari router sendiri (chain OUTPUT) belum didukung (UNSUPPORTED_CASE sesuai PRD MVP).
- Tes AppTest tidak berjalan di terminal sandbox Antigravity (soket loopback diblokir); jalankan pytest penuh di terminal biasa.
- Router tunggal; tidak ada NAT, state koneksi, atau multi-router.

## Backlog P2 (belum diimplementasikan)

Korelasi anomali untuk deteksi serangan, chain OUTPUT, NAT dan inspeksi stateful, multi-router dan routing statis, ekspor laporan otomatis, Tab-completion CLI.
