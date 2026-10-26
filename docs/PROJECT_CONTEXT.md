# PROJECT_CONTEXT

> Dokumen hidup. Agent wajib membaca file ini dan `docs/PRD.md` sebelum mengubah kode, dan memperbaruinya setelah setiap perubahan.

## Project goal
Firewall Simulator: aplikasi Python Streamlit untuk simulasi topologi jaringan, firewall/ACL, packet test, visualisasi 2D/3D, log, dan alert. Semua bersifat simulasi. Deadline akademik: 13 Nov 2026 (target aman), batas resmi 14 Nov 2026 00.00 WIB.

## Current architecture
Yang sudah diimplementasikan:
- `src/firewall_sim/core/`:
  - `models.py`: Domain entity immutable (frozen dataclass), koleksi berupa tuple, enum (DeviceType, Chain, Protocol, Action, Decision), audit log, and ProjectState.
  - `validation.py`: `validate_topology(state)` memvalidasi keabsahan IPv4 CIDR, gateway subnet, jumlah router (tepat 1 pada MVP), L2 link valid, dan mendeteksi IP duplikat.
  - `rules.py`: Evaluasi firewall berurutan (first match wins terminal action, filter enabled, port range matching, ICMP tanpa port, fallback default policy per chain).
  - `simulator.py`: `simulate_packet(state, packet, now)` deterministik, BFS L2 path traversal, same-subnet bypass firewall, router forwarding, handling chain INPUT vs FORWARD, trace langkah immutable, dan isolasi output router (UNSUPPORTED_CASE).
  - `alerts.py`: `derive_alerts(result, policy)` menghasilkan SecurityEvent bertipe FIREWALL_DROP tanpa pelabelan serangan/attack.
  - `analytics.py`: Agregasi log trafik (`TrafficLogEntry`, `create_log_entry`, `summarize_traffic`, `filter_traffic`).
- `src/firewall_sim/config/`:
  - `service.py`: `update_config(state, command)` dengan command dataclass terketik (SetInterfaceIP, SetInterfaceEnabled, SetGateway, AddRule, RemoveRule, ToggleRule, MoveRule, SetDefaultPolicy, AddDevice, RemoveDevice, RenameDevice, AddLink, RemoveLink), kenaikan config_revision atomik, audit log, ID deterministik, dan validasi topologi pre-commit.
  - `cli_parser.py`: `parse_and_execute(state, line, now)` berbasis `shlex` aman (tanpa shell execution) untuk perintah help, show, interface, gateway, rule, policy, access-list, dan test.
- `src/firewall_sim/storage/`:
  - `json_store.py`: `save_project` dan `load_project` dengan verifikasi `schema_version` dan `validate_topology`.
- `src/firewall_sim/scenarios/`:
  - `presets.py`: 4 Preset skenario lengkap (`list_scenarios()`: Web Allow, SSH Blocked, Colliding Rules, Wrong Subnet/Gateway), `default_lab()`, dan `empty_project()`.
- `src/firewall_sim/ui/`:
  - `theme.py`, `state.py`, `components.py`.
  - `viz3d.py`: Perhitungan koordinat 3D deterministik dan pembangunan frame replay step-by-step (`build_replay_frames`).
  - `pages/`: `start_here.py`, `overview.py`, `network.py`, `viz3d_page.py`, `device_config.py`, `firewall_rules.py`, `packet_sim.py`, `traffic_logs.py`, `alerts.py`, `learning_lab.py`, `cli_console.py`.
- `app.py`: Router tunggal berbasis `nav_page` dengan sidebar 4 grup (Mulai, Bangun & Konfigurasi, Simulasi & Visual, Analisis & Belajar), kartu ringkas metadata status, dan mode switcher Learning/Professional.
- `tests/`: 75 unit, acceptance, benchmark, & UI tests di `test_acceptance.py` (T01-T14), `test_benchmark.py`, `test_engine.py`, `test_config_service.py`, `test_cli_parser.py`, `test_storage.py`, `test_analytics.py`, `test_scenarios.py`, `test_viz3d.py`, `test_smoke.py`, dan `test_ui.py` (100% passed).

Planned (belum diimplementasikan / Backlog P2):
- Fitur P2 Security Alert Center: watchlist, trusted IP, ambang batas alarm berulang, auto-mitigation.
- Dukungan emulasi chain OUTPUT yang bersumber dari router (saat ini ditandai UNSUPPORTED_CASE).

## Current dependencies
Dipin di `requirements.txt` (terinstal di Python 3.13 Windows):
- `streamlit==1.66.1`: framework web UI interaktif
- `plotly==7.1.0`: visualisasi grafik 2D dan 3D
- `pytest==9.1.1`: framework unit dan regression testing
- Standard library Python murni untuk engine (`ipaddress`, `dataclasses`, `datetime`, `enum`, `typing`, `collections`, `shlex`, `math`, `re`, `json`). Tanpa dependency baru.

## Implemented features
- Core Engine & Domain Models: frozen dataclass immutable, ProjectState, SimulationResult.
- Topology Validation: pemeriksaan ketat IPv4, gateway subnet, link loop, dan batasan MVP (1 router, host 1 iface).
- Firewall Rule Evaluator: evaluasi berurutan, first match wins, port ranges, ICMP.
- Packet Simulator: penelusuran rute L2/L3, isolasi hasil (ACCEPT, DROP, NO_ROUTE, INVALID_CONFIG, UNSUPPORTED_CASE), trace per langkah.
- Security Alerts & Traffic Logs: derivasi event DROP tanpa menuduh sebagai serangan, ringkasan metrik statistik agregasi, filtering riwayat log.
- Config Service Lengkap: mutasi aman satu pintu, Add/Remove Device & Link, Rename Device, penomoran revisi atomik, audit trail.
- Preset Skenario & Learning Lab: 4 guided preset skenario dengan metadata lengkap, tombol pemuatan skenario, dan verifikasi target uji.
- Replay 3D Interaktif: Plotly Scatter3d dengan kontrol langkah demi langkah (slider & prev-next) tahan rerun; paket DROP berhenti di router.
- Mode Pembelajaran: Mode switcher Learning (panel panduan konsep) vs Professional (ringkas) tersimpan di session state tanpa memodifikasi ProjectState (T11).
- JSON Storage & Persistence: Serialisasi dan deserialisasi proyek lengkap dengan verifikasi skema dan validasi topologi.
- Antarmuka UI Streamlit Lengkap: 11 modul navigasi terintegrasi dengan router nav_page tunggal, sidebar 4 grup, Network 2D berlapis, Device Config inline valid, dan Firewall Rules terurut.

## Known bugs
Belum ada.

## Current schema
Sesuai PRD Bagian 9 dan diimplementasikan di `core/models.py`:
- `Device(id, name, type, interfaces, default_gateway)`
- `Interface(id, device_id, name, ipv4_cidr, enabled)`
- `Link(id, interface_a, interface_b, enabled)`
- `FirewallRule(id, order, enabled, chain, src_cidr, dst_cidr, protocol, src_port, dst_port, action, comment, counter)`
- `PacketTest(id, source_device_id, destination_device_id, destination_ip, protocol, src_port, dst_port, timestamp, config_revision)`
- `SimulationResult(test_id, decision, reason, matched_rule_id, trace, config_revision, timestamp, evaluated_rules)`
- `SecurityEvent(id, test_id, event_type, severity, timestamp, message, device_id, rule_id, acknowledged)`
- `ProjectState(devices, links, rules, config_revision, default_policies, scenario_metadata, audit_log)`

Usulan Perubahan Skema (Proposal untuk rilis mendatang):
- Menambahkan field `packet: Optional[PacketTest]` langsung di dalam `SimulationResult` untuk memudahkan audit jejak tanpa harus menyimpan pasangan terpisah di layer antarmuka.

## Decided
- Model data: semua dataclass frozen, koleksi berupa tuple, ProjectState tidak pernah dimutasi di tempat melainkan menghasilkan instance baru.
- Modul bawaan `ipaddress` dipakai untuk semua kalkulasi IP/subnet. Tanpa dependensi eksternal untuk core engine.
- `simulate_packet` menerima parameter `now` (callable/datetime) agar waktu pengujian deterministik.
- Default policy per chain disimpan di ProjectState (`default_policies`: input/forward/output), nilai awal ACCEPT semua (gaya MikroTik), dan tercatat dalam trace.
- Topologi MVP: host memiliki 1 interface + default_gateway; switch = L2 murni tanpa IP; tepat 1 router/firewall dengan >=1 interface ber-IP.
- Sumber router (chain OUTPUT) dikembalikan sebagai `Decision.UNSUPPORTED_CASE` dan dicatat sebagai backlog MVP.
- Replay 3D menggunakan Scatter3d dengan kontrol manual step-by-step (slider/prev-next) agar tahan terhadap rerun Streamlit dan mendukung opsi pengurangan animasi.
- Mode antarmuka (Learning vs Professional) disimpan murni di session_state dan tidak menyentuh ProjectState (T11).

## Pending decisions
- Model visual 3D advance (glTF mesh jika diperlukan, ditunda karena Scatter3d sudah memenuhi PRD dan ADR-001)

## Next tasks
1. [Selesai] Scaffolding proyek
2. [Selesai] Engine murni + unit tests (T01–T05, T08–T09, T12–T13)
3. [Selesai] UI Streamlit, GUI rules, CLI subset, 2D (T06–T07)
4. [Selesai] 3D Replay, Traffic Logs, Security Alert Center, Learning Lab, JSON Storage, Mode Switcher (T10–T11)
5. Persiapan pelaporan akhir akademik dan demo aplikasi.

## Commands to run/test
```powershell
# Inisialisasi virtualenv (Windows)
python -m venv .venv
.\.venv\Scripts\activate

# Instalasi dependensi
pip install -r requirements.txt

# Menjalankan pengujian unit / smoke test
pytest

# Menjalankan aplikasi Streamlit
streamlit run app.py
```

## Last verified commit/version
Tahap R1 Selesai (2026-10-26). Pytest 77 passed (100% lulus). Eliminasi emoji 100%, bug judul halaman dinormalisasi, form topologi divalidasi, dan UI audit 31 poin terdokumentasi di docs/UI_AUDIT.md.