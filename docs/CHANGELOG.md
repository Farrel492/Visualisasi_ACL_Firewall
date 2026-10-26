# CHANGELOG

Format tiap entri: Date; version; Added/Changed/Fixed; impacted modules; tests performed; known limitations; next steps.

## [Unreleased]

### 2026-10-26: Tahap R2 - Workflow Rail, CSS Design System, dan Audit Log Dasbor
- **Added:**
  - `src/firewall_sim/ui/theme.py` — `inject_theme_css()`: Menghasilkan CSS design system `.fw-*` dengan token CSS variabel, workflow rail, card hover, badge monospace, terminal window frame, dan `@media (prefers-reduced-motion)` untuk aksesibilitas.
  - `src/firewall_sim/ui/components.py` — `render_workflow_rail(current_page)`: Menampilkan bilah 5 langkah horizontal (Build → Configure → Simulate → Visualize → Analyze) dengan langkah aktif di-highlight; `render_flow_next(page, label, hint)`: Tombol navigasi "Lanjut: <halaman>" di akhir setiap konten halaman.
  - `tests/test_ui.py` — `test_ui_workflow_rail_and_flow_next`: Pengujian verifikasi keberadaan workflow rail di halaman network dan fungsionalitas tombol flow next.
- **Changed:**
  - `src/firewall_sim/ui/pages/start_here.py`: Hero dipadatkan (3 kalimat teknis), panduan konsep dipindahkan ke expander yang muncul hanya di Learning Mode, tombol langkah stepper lebih ikonis (icon + label pendek). Ditambahkan `render_flow_next`.
  - `src/firewall_sim/ui/pages/overview.py`: Ditambahkan kartu riwayat 5 revisi audit log konfigurasi terakhir. Ditambahkan `render_flow_next`.
  - `src/firewall_sim/ui/pages/network.py`, `firewall_rules.py`, `packet_sim.py`, `viz3d_page.py`, `traffic_logs.py`: Ditambahkan `render_workflow_rail` dan `render_flow_next` untuk memberikan alur navigasi berurutan yang terarah.
  - `src/firewall_sim/ui/components.py`: Penambahan `inject_theme_css()` di dalam `page_header` agar CSS design system diinjeksikan di setiap halaman.
- **Impacted modules:** `ui/theme.py`, `ui/components.py`, `ui/pages/start_here.py`, `ui/pages/overview.py`, `ui/pages/network.py`, `ui/pages/firewall_rules.py`, `ui/pages/packet_sim.py`, `ui/pages/viz3d_page.py`, `ui/pages/traffic_logs.py`, `tests/test_ui.py`.
- **Tests performed:** `pytest` 78 passed in 9.32s (100% lulus, +1 tes baru).
- **Known limitations:** Animasi CSS (fade/slide), gaya terminal actual, dan rendering Plotly/3D tidak dapat diverifikasi pada headless AppTest.
- **Next steps:** Tahap R3 - Konsol CLI bergaya terminal nyata (window frame, monospace prompt, output berwarna per jenis, riwayat per sesi).

### 2026-10-26: Tahap R1 - Perbaikan Bug P0, Kejelasan Topologi, dan Eliminasi Emoji
- **Added:**

  - `docs/UI_AUDIT.md`: Dokumen audit antarmuka 31 item mencatat reproduksi bug, pesan error asli, dan verifikasi fitur interaktif.
  - `src/firewall_sim/ui/assets/logo.svg` & `src/firewall_sim/ui/assets/icon.svg`: Asset visual SVG tanpa dependensi eksternal untuk integrasi `st.logo`.
  - `tests/test_ui.py`: Penambahan pengujian verifikasi form CRUD topologi (`test_ui_topology_crud_actions`) dan perbedaan elemen mode Learning vs Professional (`test_ui_learning_vs_professional_mode_elements`).
- **Changed:**
  - `src/firewall_sim/ui/components.py`: Normalisasi `page_header(title, description)` agar menampilkan judul spesifik per halaman; penghapusan chip header yang membingungkan.
  - `app.py`: Penambahan `st.logo()`, penyederhanaan banner sidebar ke satu baris `st.info` dengan popover penjelasan, pemindahan status revisi/topologi ke kartu status sidebar, dan eliminasi catatan duplikat di kaki sidebar.
  - `.streamlit/config.toml`: Penambahan konfigurasi `toolbarMode = "minimal"` dan `gatherUsageStats = false` untuk menyembunyikan tombol deploy/menu berlebih.
  - `src/firewall_sim/ui/state.py`: Penambahan helper `is_learning()` untuk mendeteksi mode edukatif.
  - `src/firewall_sim/ui/pages/network.py`: Perbaikan form Tambah Perangkat dengan field input IP dan gateway untuk PC/Server (mencegah error HOST_MISSING_IP); perbaikan form Tambah Link dengan pesan informatif saat port penuh; pembersihan tampilan enum mentah `DeviceType.PC`.
  - Seluruh halaman UI, teks, dan dokumentasi: Eliminasi total karakter emoji, digantikan dengan Material Symbols (`:material/name:`) atau styling CSS murni.
- **Fixed:**
  - Judul halaman seragam "Mulai di Sini" pada semua halaman kini menampilkan judul spesifik masing-masing halaman.
  - Form Tambah Perangkat gagal menambah host karena ketiadaan input IP dan gateway.
  - Tampilan enum mentah pada opsi pemilihan jenis perangkat.
- **Impacted modules:** `app.py`, `.streamlit/config.toml`, `src/firewall_sim/ui/*`, `tests/test_ui.py`, `docs/*`.
- **Tests performed:** `pytest` 77 passed in 11.10s (100% lulus).
- **Known limitations:** Kesalahan browser pihak ketiga (seperti ekstensi auto-translate Google Translate yang menyebabkan error `removeChild` pada React DOM) tidak dapat direproduksi langsung pada pengujian headless.
- **Next steps:** Tahap R2 - Redesain UI, alur kerja (workflow rail), penyederhanaan teks panduan, dan penghapusan kesan template AI.

### 2026-10-25: Tahap D - Regression Testing, Benchmarking, and Comprehensive Documentation
- **Added:**
  - `tests/test_acceptance.py`: 14 pengujian penerimaan lengkap memetakan 1:1 ke PRD Bagian 12 (`test_T01` hingga `test_T14`), mencakup ACCEPT/DROP, rule order (first match wins), rule nonaktif, mutasi IP interface, sinkronisasi CLI & GUI, perutean NO_ROUTE, penolakan CIDR tidak valid (state tidak rusak), 3D replay berhenti di firewall, isolasi mode UI, pelabelan event DROP non-serangan, audit revisi atomik, dan keamanan parser CLI tanpa eksekusi subprocess.
  - `tests/test_benchmark.py`: Pengujian tolok ukur performa pada skala 10 perangkat + 50 aturan firewall (`simulate_packet`: 0.3479 ms per panggilan; `AppTest` render halaman penuh: 0.5419 s) tanpa ambang batas sintetis.
  - `docs/USER_GUIDE.md`: Panduan pengguna komprehensif dalam Bahasa Indonesia (alur kerja 5 langkah, skrip demonstrasi 10 menit, tabel referensi perintah CLI, glosarium teknis, dan FAQ diagnostik).
  - `docs/TEST_REPORT.md`: Laporan formal pengujian perangkat lunak memuat tabel matriks status T01-T14 riil, tolok ukur benchmark, rekapitulasi 75 tes, keterbatasan peramban Playwright, dan backlog fitur P2.
- **Changed:**
  - `README.md`: Pembaruan dokumentasi alur kerja, tautan panduan pengguna, dan laporan uji terbaru.
- **Impacted modules:** `tests/test_acceptance.py`, `tests/test_benchmark.py`, `docs/USER_GUIDE.md`, `docs/TEST_REPORT.md`, `README.md`, `docs/PROJECT_CONTEXT.md`.
- **Tests performed:** `pytest` 75 passed in 12.01s (100% lulus, 0 gagal, 0 warning/error).
- **Known limitations:** Keterbatasan browser otomatis Playwright pada lingkungan runtime; seluruh verifikasi struktur visual diverifikasi lewat AppTest. Fitur P2 (canvas drag-and-drop, rate limit alert, model glTF) dicatat sebagai backlog terpisah.
- **Next steps:** Penyusunan laporan akhir akademik dan persiapan demo produk.

### 2026-10-25: Tahap C - Packet Simulation, 3D Visualization, Logs, Alerts, Learning Lab, and CLI Console
- **Changed:**
  - `src/firewall_sim/ui/pages/packet_sim.py`: Penambahan 3 tombol uji cepat (PC A -> Server Web, PC B -> Server Web, PC A -> PC B ICMP), kartu hasil evaluasi beraksen border kiri dengan warna sesuai keputusan (ACCEPT hijau, DROP merah, NO_ROUTE amber), headline tebal satu baris, badge status, tombol lompat ke 3D/Log, expander jejak bernomor, dan pelabelan revisi lama yang usang.
  - `src/firewall_sim/ui/pages/viz3d_page.py`: Pemilihan otomatis hasil uji simulasi terbaru (index 0), tata letak berdampingan 2:1 antara panggung Scatter3d dan panel keputusan teks, chip legenda spasial (Router Z=0, Switch Z=1, PC/Server Z=2, Paket Z-pos), slider penelusuran langkah frame-by-frame, dan penegasan bahwa paket DROP berhenti di router.
  - `src/firewall_sim/ui/pages/traffic_logs.py`: Baris KPI ber-border, integrasi `st.dataframe` dengan `column_config` berbahasa Indonesia, `hide_index=True`, filter status dan pencarian IP, serta tautan navigasi.
  - `src/firewall_sim/ui/pages/alerts.py`: Mempertahankan teks peringatan standar bahwa penolakan (DROP) adalah kebijakan normal bukan otomatis serangan (PRD Bagian 11/12), toggle penandaan highlight, dan penataan kartu insiden.
  - `src/firewall_sim/ui/pages/learning_lab.py`: Standardisasi kartu skenario praktik, tombol eksekusi uji terpadu, dan verifikasi target pembelajaran.
  - `src/firewall_sim/ui/pages/cli_console.py`: Daftar perintah cepat klik-untuk-isi (`show running-config`, `help`, `show rules`, `test`), terminal output rapi, dan tombol navigasi.
  - `src/firewall_sim/ui/pages/overview.py`: Kartu metrik KPI ber-border, kartu validasi topologi, dan persistensi berkas JSON.
  - `tests/test_ui.py`: Penambahan pengujian verifikasi AppTest untuk ketiadaan dict mentah di seluruh 11 halaman, keberadaan page_header, serta tombol navigasi pada empty state.
- **Fixed:** Penyesuaian nama atribut `ReplayFrame` (`position`, `device_id`, `path_so_far`) pada visualisasi 3D.
- **Impacted modules:** `ui/pages/packet_sim.py`, `ui/pages/viz3d_page.py`, `ui/pages/traffic_logs.py`, `ui/pages/alerts.py`, `ui/pages/learning_lab.py`, `ui/pages/cli_console.py`, `ui/pages/overview.py`, `tests/test_ui.py`.
- **Tests performed:** `pytest` 60 passed in 11.47s (100% lulus tanpa kegagalan).
- **Known limitations:** Visual rendering interaksi 3D peramban belum terverifikasi secara visual langsung karena driver Playwright; fungsionalitas direpresentasikan penuh pada AppTest.
- **Next steps:** Tahap D - Regresi & Dokumentasi (test_acceptance.py untuk T01-T14, test_benchmark.py, USER_GUIDE.md, TEST_REPORT.md, dan README.md).

### 2026-10-25: Tahap B - Network 2D, Device Config, and Firewall Rules
- **Changed:**
  - `src/firewall_sim/ui/pages/network.py`: Tata letak graf Plotly 2D berlapis deterministik (PC di kiri, switch, router di tengah-kanan dengan marker diamond menonjol, server di kanan), link 3px dengan warna muted, tinggi graf 520px, chip legenda tipe di atas graf, inspector perangkat terstruktur, dan form manajemen topologi dipindahkan ke panel samping/expander ber-container.
  - `src/firewall_sim/ui/pages/device_config.py`: Form konfigurasi per perangkat dengan perbandingan nilai saat ini vs baru, validasi inline IPv4/CIDR berbahasa Indonesia, penanganan switch L2 tanpa IP, dan penguncian input tidak valid (T09).
  - `src/firewall_sim/ui/pages/firewall_rules.py`: Banner default policy per chain (FORWARD, INPUT, OUTPUT), teks penegasan urutan evaluasi ("Dievaluasi dari atas ke bawah; rule pertama yang cocok menang"), tabel rule per chain dengan kolom berbahasa Indonesia, penandaan status nonaktif berlabel teks eksplisit, form tambah rule terstruktur, dan tombol naik/turun/aktif/hapus dengan key stabil.
  - Setiap halaman mengintegrasikan `page_header`, `empty_state` dengan tombol aksi terarah, `next_steps` di panel kanan, dan umpan balik `st.toast`/`render_error_box`.
- **Fixed:** Form konfigurasi pada Network 2D dan Firewall Rules tidak lagi mendominasi viewport, menjaga fokus visual pada graf dan daftar aturan.
- **Impacted modules:** `ui/pages/network.py`, `ui/pages/device_config.py`, `ui/pages/firewall_rules.py`.
- **Tests performed:** `pytest` 58 passed in 5.66s (100% lulus tanpa regresi).
- **Known limitations:** Visual rendering CSS Plotly pada browser klien belum terverifikasi secara langsung akibat kendala Playwright runtime driver; fungsionalitas dan integritas state divalidasi via unit test & AppTest.
- **Next steps:** Tahap C - Packet Simulation, 3D Visualization, Traffic Logs, Alert Center, Learning Lab, and CLI Console.

### 2026-10-25: Tahap A - Fondasi UI, Navigasi Grup, dan Halaman "Mulai di Sini"
- **Added:**
  - `src/firewall_sim/ui/pages/start_here.py`: Halaman "Mulai di Sini" dengan hero banner, alur singkat 3 kalimat, stepper 5 kartu horizontal (Build, Configure, Simulate, Visualize, Analyze), dan tombol muat demo siap pakai serta mulai proyek kosong.
  - `src/firewall_sim/ui/state.py`: Helper `clear_simulation_data()`, `load_demo_scenario()` (mereset ke lab default, menyuntikkan 2 rule lewat apply_command, dan menjalankan pengujian paket otomatis), serta manajemen routing `nav_page`.
- **Changed:**
  - `.streamlit/config.toml`: Penerapan tema visual dark (#0F172A, #1E293B, #0B1220 sidebar, primary #3B82F6, border #334155, baseRadius 0.75rem).
  - `src/firewall_sim/ui/theme.py`: Penyelarasan token warna, radius, dan spacing tokens.
  - `src/firewall_sim/ui/components.py`: Penghapusan duplikasi banner simulasi, standardisasi `page_header` dengan status chips (revisi, mode, validasi), penyesuaian `status_badge`, `empty_state` dengan routing `nav_page`, `next_steps`, serta glosarium `tooltip`.
  - `app.py`: Router tunggal berbasis `nav_page` dengan sidebar terbagi dalam 4 grup navigasi (Mulai, Bangun & Konfigurasi, Simulasi & Visual, Analisis & Belajar) menggunakan tombol ber-key stabil dan indikator aktif.
  - `tests/test_ui.py`: Migrasi pencarian widget ke key stabil, pengujian render `start_here` dan `page_header`, serta pengujian otomasi skenario demo (menghasilkan >=1 ACCEPT, >=1 DROP, >=1 alert).
- **Fixed:**
  - Duplikasi peringatan `st.warning` pada `render_simulation_banner()`.
  - Ketidaksinkronan target navigasi pada `empty_state` dan `next_steps` terhadap router aplikasi.
- **Impacted modules:** `.streamlit/config.toml`, `ui/theme.py`, `ui/components.py`, `ui/state.py`, `ui/pages/start_here.py`, `app.py`, `tests/test_ui.py`.
- **Tests performed:** `pytest` 58 passed in 11.50s (100% lulus tanpa kegagalan).
- **Known limitations:** Tampilan visual browser belum terverifikasi secara langsung akibat dependensi driver browser Playwright yang tidak dapat diunduh di lingkungan runtime; seluruh verifikasi struktur elemen, integrasi router, dan state divalidasi via Streamlit AppTest.
- **Next steps:** Tahap B - Penataan Network 2D (Plotly layout & chip legenda), Device Config form inline, dan Firewall Rules tabel berurut dengan banner default policy.

### 2026-10-24: 3D Replay, Traffic Logs, Security Alert Center, Learning Lab, JSON Storage & Mode Switcher
- **Added:**
  - `src/firewall_sim/storage/json_store.py`: Persistence `save_project` dan `load_project` dengan validasi struktur data, `schema_version="1.0"`, dan `validate_topology`.
  - `src/firewall_sim/scenarios/presets.py`: 4 Preset skenario lengkap dengan metadata instruksional (`list_scenarios()`: Web Allow, SSH Blocked, Colliding Rules, Wrong Subnet/Gateway).
  - `src/firewall_sim/core/analytics.py`: Agregasi dan pencatatan log trafik murni Python (`TrafficLogEntry`, `create_log_entry`, `summarize_traffic`, `filter_traffic`).
  - `src/firewall_sim/ui/viz3d.py`: Modul murni Python kalkulasi posisi 3D deterministik (`Point3D`, Z-level per tipe perangkat) dan pembentukan `build_replay_frames` (T10: DROP berhenti di router).
  - `src/firewall_sim/ui/pages/viz3d_page.py`: Visualisasi Plotly Scatter3d interaktif dengan replay frame langkah-demi-langkah (slider / tombol prev-next) tahan terhadap rerun Streamlit.
  - `src/firewall_sim/ui/pages/traffic_logs.py`: Dashboard analitik log trafik dengan metrik statistik agregasi dan filter keputusan / IP.
  - `src/firewall_sim/ui/pages/alerts.py`: Security Alert Center untuk peninjauan event DROP dengan teks peringatan permanen non-serangan dan toggle highlight.
  - `src/firewall_sim/ui/pages/learning_lab.py`: Halaman skenario interaktif dengan tombol muat otomatis dan pengujian target skenario.
  - `src/firewall_sim/ui/pages/overview.py`: Integrasi tombol unduh (simpan) dan unggah (muat) berkas JSON, metrik log, dan ringkasan alert.
  - Sidebar Mode Switcher (`app.py`): Pilihan Learning Mode (panel penjelasan konsep edukatif) vs Professional Mode (tampilan ringkas) yang tersimpan murni di `session_state` tanpa mengubah `ProjectState` (T11).
  - Unit & Integration Tests:
    - `tests/test_storage.py`: Round-trip serialisasi/deserialisasi JSON dan error handling berkas korup.
    - `tests/test_analytics.py`: Pengujian agregasi statistik, filter log, T12 non-serangan, dan T13 level versi log.
    - `tests/test_scenarios.py`: Validasi hasil simulasi untuk ke-4 preset skenario dan T11 isolasi state mode UI.
    - `tests/test_viz3d.py`: Validasi T10 (frame DROP berhenti di router) dan elevasi Z deterministik.
    - `tests/test_ui.py`: Tes integrasi Streamlit `AppTest` untuk seluruh 10 modul navigasi dan interaksi mode.
- **Changed:** `app.py`, `ui/state.py`, `ui/pages/firewall_rules.py`, `ui/pages/packet_sim.py`, `README.md`.
- **Fixed:** -
- **Impacted modules:** `storage/*`, `scenarios/*`, `core/analytics.py`, `ui/viz3d.py`, `ui/pages/*`, `app.py`, `tests/*`, `README.md`.
- **Tests performed:**
  - `pytest`: 57 passed in 9.23s (100% lulus, mencakup seluruh unit test, smoke test, dan AppTest UI).
  - Headless Streamlit: server terverifikasi aktif di port 8503 tanpa crash/exception.
- **Known limitations:** Tampilan visual grafis dan kehalusan orbit rotasi 3D pada peramban klien tidak dapat diamati secara visual langsung oleh AI agent.
- **Next steps:** Pengujian regresi akhir, penyusunan dokumentasi laporan tugas, dan persiapan demo.
- **Added:**
  - `src/firewall_sim/config/service.py`: Penambahan command terketik baru `AddDevice`, `RemoveDevice` (cascade link & tolak hapus satu-satunya router), `RenameDevice`, `AddLink`, `RemoveLink` dengan ID deterministik.
  - `src/firewall_sim/scenarios/presets.py`: Modul preset `default_lab()` dan `empty_project()`.
  - `src/firewall_sim/config/cli_parser.py`: Parser CLI berbasis `shlex` aman tanpa eval/exec/subprocess untuk perintah `help`, `show`, `interface`, `gateway`, `rule`, `policy`, `access-list` (translasi ke kanonik), dan `test`.
  - `src/firewall_sim/ui/`:
    - `theme.py`: Definisi token warna PRD 11 dan badge keputusan teks+ikon.
    - `state.py`: Jembatan tunggal UI ke engine melalui `apply_command`, riwayat pengujian, dan event keamanan.
    - `components.py`: Banner peringatan simulasi permanen dan render error.
    - `pages/overview.py`: Ringkasan topologi, metrics, status validasi, dan reset preset.
    - `pages/network.py`: Visualisasi Plotly 2D deterministik (router di tengah, host/switch melingkar), inspector perangkat, dan form topologi.
    - `pages/device_config.py`: Form IP interface, shutdown/no shutdown, dan default gateway host.
    - `pages/firewall_rules.py`: Tabel rules per chain, form tambah rule, manajemen order naik/turun, toggle, dan default policy per chain.
    - `pages/packet_sim.py`: Generator paket virtual, evaluasi simulator, badge keputusan, trace langkah, dan pelabelan revisi pada riwayat.
    - `pages/cli_console.py`: Terminal interaktif bergaya shell.
  - `.streamlit/config.toml`: Tema kustom palet PRD 11 (`#111827`, `#1E293B`, `#3B82F6`).
  - `tests/test_config_service.py`: Tes penambahan/penghapusan device/link dan perlindungan router tunggal.
  - `tests/test_cli_parser.py`: Tes T06, T07, T14 (input berbahaya dan perintah tak dikenal), translasi ACL, dan simulasi paket via CLI.
  - `tests/test_ui.py`: Tes integrasi UI menggunakan Streamlit `AppTest` (render seluruh halaman dan jembatan state CLI/GUI).
- **Changed:** `app.py` diperbarui sebagai controller navigasi sidebar stabil.
- **Fixed:** -
- **Impacted modules:** `src/firewall_sim/config/*`, `src/firewall_sim/scenarios/*`, `src/firewall_sim/ui/*`, `tests/*`, `app.py`, `README.md`.
- **Tests performed:**
  - `pytest`: 38 passed in 3.94s (unit test engine, CLI parser, config service, smoke test, dan AppTest UI).
  - Headless Streamlit: server berhasil dijalankan di port 8502 tanpa exception.
- **Known limitations:** Visualisasi 3D, Security Alert Center terdedikasi, dashboard log analitik penuh, Learning Mode terpadu, dan ekspor/impor JSON belum diimplementasikan (direncanakan pada prompt berikutnya). Tampilan visual browser tidak dapat diverifikasi secara langsung oleh CLI agent.
- **Next steps:** Implementasi visualisasi 3D Plotly, Security Alert Center, dashboard analytics, dan modul Learning Mode.
- **Added:**
  - `src/firewall_sim/core/models.py`: Implementasi frozen dataclass immutable (Device, Interface, Link, FirewallRule, PacketTest, SimulationResult, SecurityEvent, AuditEntry, ProjectState) dan Enum domain.
  - `src/firewall_sim/core/validation.py`: `validate_topology(state)` untuk IPv4, keunikan ID/nama, validitas link L2, batasan 1 router, subnet gateway host, dan deteksi IP duplikat.
  - `src/firewall_sim/core/rules.py`: Engine evaluasi rule berurutan, first matching terminal action, filter enabled, port ranges, ICMP, dan fallback default policy per chain.
  - `src/firewall_sim/core/simulator.py`: `simulate_packet(state, packet, now)` deterministik, BFS L2 traversal, same-subnet bypass firewall, router forwarding, isolasi hasil (ACCEPT, DROP, NO_ROUTE, INVALID_CONFIG, UNSUPPORTED_CASE), trace per langkah.
  - `src/firewall_sim/core/alerts.py`: `derive_alerts(result, policy)` untuk event FIREWALL_DROP tanpa label serangan.
  - `src/firewall_sim/config/service.py`: `update_config(state, command)` dengan command terketik, kenaikan config_revision atomik, audit log, dan validasi topologi pre-commit.
  - `tests/conftest.py`: Fixture topologi contoh standar MVP (PC A, PC B, Switch LAN, Router Firewall, Web Server).
  - `tests/test_engine.py`: 19 unit test mencakup T01–T05, T08, T09, T12, T13, determinisme, imutabilitas, default policy, port range, ICMP, same-subnet bypass, gateway validation, dan router input chain.
- **Changed:** -
- **Fixed:** Penanganan prioritas traffic ke IP interface router diarahkan ke chain INPUT sebelum pemeriksaan same-subnet host-to-host.
- **Impacted modules:** `src/firewall_sim/core/*`, `src/firewall_sim/config/service.py`, `tests/*`, `docs/PROJECT_CONTEXT.md`, `docs/CHANGELOG.md`.
- **Tests performed:**
  - `pytest`: 21 passed in 0.12s (19 unit test engine/service + 2 smoke test).
- **Known limitations:** UI Streamlit belum terhubung ke engine; CLI parser, persistensi storage, dan visualisasi 2D/3D belum diimplementasikan; paket dari router (chain output) belum didukung (UNSUPPORTED_CASE).
- **Next steps:** Integrasi UI Streamlit, rule GUI, CLI subset parser, dan visualisasi topologi 2D.
- **Added:**
  - Struktur paket `src/firewall_sim/` (`core/`, `config/`, `storage/`, `scenarios/`, `ui/`) beserta `__init__.py` di setiap level.
  - Modul placeholder di `core/` (`models.py`, `validation.py`, `rules.py`, `simulator.py`, `alerts.py`) dengan docstring kontrak PRD & AGENTS.md + TODO.
  - Modul placeholder di `config/` (`service.py`, `cli_parser.py`) dengan docstring kontrak PRD & AGENTS.md + TODO.
  - Smoke test di `tests/test_smoke.py` untuk verifikasi import paket dan kepatuhan arsitektur engine (murni Python, bebas import library UI).
  - Entry point Streamlit minimal di `app.py` dengan banner status simulasi dan scaffolding.
  - Konfigurasi `pytest.ini` (`pythonpath = src`), `.gitignore`, dan `requirements.txt` (dipin ke versi nyata).
- **Changed:** -
- **Fixed:** -
- **Impacted modules:** seluruh struktur direktori proyek, `src/firewall_sim/*`, `tests/*`, `app.py`, `requirements.txt`, `pytest.ini`, `.gitignore`.
- **Tests performed:**
  - `pytest`: 2 passed (smoke test import seluruh package dan pemeriksaan AST larangan import UI pada modul core).
  - `streamlit run app.py --server.headless true`: Uvicorn server berhasil jalan di `http://localhost:8501`.
- **Known limitations:** scaffolding saja, belum ada logika engine, rule evaluation, simulator paket, parser CLI, GUI lengkap, maupun visualisasi 2D/3D.
- **Next steps:** implementasi engine murni dan model data di `core/` beserta unit tests T01–T05, T08–T09.

### 2026-10-24: PRD v1.0 baseline
- **Added:** `docs/PRD.md`, `docs/PROJECT_CONTEXT.md`, `docs/CHANGELOG.md`, `docs/adr/ADR-001-hybrid-2d-3d.md`, `AGENTS.md`, `README.md`
- **Changed:** -
- **Fixed:** -
- **Impacted modules:** dokumentasi saja
- **Tests performed:** -
- **Known limitations:** belum ada kode
- **Next steps:** scaffolding proyek