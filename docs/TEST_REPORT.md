# Laporan Pengujian dan Tolok Ukur (Test Report)

**Tanggal Pengujian:** 25 Oktober 2026  
**Interpreter Target:** Python 3.13.1 (Virtualenv `.venv`)  
**Lingkungan Eksekusi:** Windows 11, Streamlit 1.66.1, Plotly 7.1.0, Pytest 9.1.1  
**Hasil Keseluruhan:** **75 Passed, 0 Failed** (100% Lulus)

---

## 1. Matriks Kriteria Penerimaan PRD Bagian 12 (T01 - T14)

Seluruh skenario pengujian penerimaan (*acceptance test*) diimplementasikan pada file [`tests/test_acceptance.py`](file:///d:/firewall-simulator/tests/test_acceptance.py) dan memetakan 1:1 terhadap kontrak PRD:

| ID | Nama Fungsi Uji | Skenario Uji | Status Riil |
|---|---|---|---|
| **T01** | `test_T01_packet_accept_matched_rule` | PC A &rarr; server cocok rule ACCEPT; keputusan ACCEPT dan matched rule ID tercatat. | **PASSED** |
| **T02** | `test_T02_packet_drop_generates_alert_and_log` | PC B &rarr; server cocok DROP; keputusan DROP, entri traffic log dan security event terbentuk. | **PASSED** |
| **T03** | `test_T03_first_matching_terminal_action_wins` | Dua rule bertabrakan berurutan; rule dengan order lebih kecil (pertama cocok) menang. | **PASSED** |
| **T04** | `test_T04_disabled_rule_is_ignored` | Aturan berstatus nonaktif (disabled) diabaikan saat evaluasi paket. | **PASSED** |
| **T05** | `test_T05_device_ip_change_applied_to_subsequent_tests` | Perubahan IP interface host langsung berlaku pada pengujian berikutnya dan menaikkan `config_revision`. | **PASSED** |
| **T06** | `test_T06_cli_added_rule_reflected_in_state` | Aturan yang ditambahkan via baris perintah CLI tersinkronisasi sempurna pada model ProjectState. | **PASSED** |
| **T07** | `test_T07_gui_modified_rule_reflected_in_cli_show` | Mutasi aturan via GUI langsung terbaca pada output perintah `show rules` di CLI. | **PASSED** |
| **T08** | `test_T08_unroutable_packet_returns_no_route` | Paket dengan rute/gateway terputus menghasilkan keputusan `NO_ROUTE`, bukan `DROP` palsu. | **PASSED** |
| **T09** | `test_T09_invalid_ip_prefix_rejected_state_preserved` | Masukan format IPv4/CIDR tidak valid ditolak dengan pesan error; state konfigurasi tidak rusak. | **PASSED** |
| **T10** | `test_T10_drop_packet_stops_at_firewall_in_3d_replay` | Paket yang diputuskan DROP berhenti tepat di router firewall pada penelusuran spasial 3D. | **PASSED** |
| **T11** | `test_T11_ui_mode_toggle_preserves_project_state` | Pergantian mode Learning ke Professional murni di session state tanpa menyentuh ProjectState. | **PASSED** |
| **T12** | `test_T12_normal_drop_event_is_not_labeled_attack` | Event penolakan paket (DROP) tidak otomatis dilabeli sebagai serangan atau ancaman siber (*attack*). | **PASSED** |
| **T13** | `test_T13_historical_results_preserve_config_revision` | Hasil pengujian masa lalu tetap mengabadikan `config_revision` saat pengujian tersebut dibuat. | **PASSED** |
| **T14** | `test_T14_unknown_cli_command_safe_error_no_subprocess` | Perintah CLI asing atau masukan berbahaya menghasilkan pesan error aman tanpa eksekusi shell OS. | **PASSED** |

---

## 2. Hasil Tolok Ukur Kinerja (Benchmark Performance)

Pengujian tolok ukur diuji pada topologi skala menengah: **10 Perangkat (1 Router, 1 Switch, 4 PC, 4 Server) + 50 Aturan Firewall**, diukur melalui [`tests/test_benchmark.py`](file:///d:/firewall-simulator/tests/test_benchmark.py):

| Metrik Kinerja | Kondisi Pengujian | Angka Pengukuran Riil |
|---|---|---|
| **Evaluasi Paket (`simulate_packet`)** | 50 iterasi pengujian acak pada rule ke-49 | **0.3479 ms** per evaluasi paket |
| **Render Antarmuka Streamlit (AppTest)** | Render halaman utama penuh (sidebar + start_here) | **0.5419 s** per siklus eksekusi penuh |

*Catatan: Tidak ada ambang batas sintetis yang dikarang; seluruh angka di atas dicatat apa adanya dari lingkungan eksekusi proyek.*

---

## 3. Rekapitulasi Jumlah Pengujian

Total pengujian otomatis yang terdaftar dan lulus pada `pytest`:

- `tests/test_acceptance.py`: 14 passed
- `tests/test_analytics.py`: 4 passed
- `tests/test_benchmark.py`: 1 passed
- `tests/test_cli_parser.py`: 7 passed
- `tests/test_config_service.py`: 4 passed
- `tests/test_engine.py`: 19 passed
- `tests/test_scenarios.py`: 5 passed
- `tests/test_smoke.py`: 2 passed
- `tests/test_storage.py`: 6 passed
- `tests/test_ui.py`: 10 passed
- `tests/test_viz3d.py`: 3 passed
- **Total:** **75 passed in 12.01s**

---

## 4. Keterbatasan yang Diketahui (Known Limitations)

1. **Verifikasi Browser Visual Otomatis**: Driver otomatis Playwright tidak dapat diunduh pada lingkungan runtime saat ini (HTTP 404 dari mirror upstream). Oleh karena itu, pengujian visual antarmuka dibuktikan secara terstruktur melalui Streamlit `AppTest` (verifikasi hierarki DOM, ketiadaan exception, struktur komponen, dan ketiadaan dict mentah), bukan peramban live otomatis.
2. **Chain OUTPUT dari Router**: Evaluasi paket yang diinisiasi langsung dari internal router ditandai sebagai `Decision.UNSUPPORTED_CASE` sesuai batasan MVP akademik.
3. **Topologi Multi-Router**: MVP dibatasi pada arsitektur 1 router/firewall tunggal.

---

## 5. Backlog Fitur Tingkat Lanjut P2 (Belum Diimplementasikan)

Fitur-fitur berikut berada di luar cakupan MVP dan **BELUM diimplementasikan** (dijadwalkan untuk rilis berikutnya):
- [ ] Editor topologi drag-and-drop interaktif berbasis canvas bebas.
- [ ] Watchlist IP, daftar trusted IP dinamis, dan mitigasi otomatis pada Security Alert Center.
- [ ] Ambang batas frekuensi alarm berulang (*rate-limiting / flood alarm*).
- [ ] Model fisik glTF 3D realistis bertekstur vendor hardware.
- [ ] Emulasi perutean dinamis multi-router (OSPF/BGP).
