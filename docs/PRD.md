# Firewall Simulator: Product Requirements Document

**Versi:** 1.0 · **Tanggal baseline:** 24 Oktober 2026 · **Status:** Approved Direction / Living Document
**Target tugas:** sebelum 14 November 2026, 00.00 WIB

> Dokumen ini adalah spesifikasi produk dan handoff implementasi, bukan laporan tugas maksimal 10 halaman. Laporan akademik disusun terpisah sesuai petunjuk dosen.

## 1. Ringkasan Eksekutif

Firewall Simulator adalah aplikasi berbasis Python Streamlit untuk membangun topologi jaringan virtual, mengonfigurasi perangkat dan aturan firewall/ACL, mensimulasikan aliran paket, dan memahami keputusan ACCEPT/DROP melalui workspace 2D, visualisasi 3D, log, serta notifikasi. Produk melayani dua kelompok: pengguna yang belajar networking dan pengguna berpengalaman yang membutuhkan eksperimen kebijakan secara efisien.

Semua aktivitas adalah **SIMULASI**. MVP tidak menangkap paket jaringan produksi, tidak menjalankan Cisco IOS/RouterOS asli, dan bukan sistem IDS/NOC operasional.

## 2. Visi, Misi, dan Tujuan

**Visi:** Menjadi platform simulasi keamanan jaringan yang profesional, interaktif, dan mudah diakses berbagai tingkat pengguna, dengan menggabungkan konfigurasi infrastruktur virtual, pengelolaan ACL/firewall, visualisasi trafik 2D/3D, dan monitoring keamanan berbasis simulasi.

**Misi:**
- Mempermudah pemahaman firewall, ACL, addressing, dan troubleshooting melalui demonstrasi yang dapat diulang.
- Menyediakan konfigurasi CLI bergaya Cisco dan GUI terinspirasi MikroTik yang tersinkron pada satu model data.
- Memvisualisasikan perangkat, koneksi, perjalanan paket, titik penolakan, dan rule yang cocok.
- Menyediakan log serta alert yang menjelaskan peristiwa, bukan sekadar warna merah/hijau.
- Menjaga arsitektur modular dan dokumentasi yang mudah dilanjutkan oleh pengembang atau AI lain.

| Tujuan | Indikator keberhasilan |
|---|---|
| Akademik | Aplikasi Python Streamlit berjalan, mendemonstrasikan allow/deny, dan dapat dijelaskan dalam laporan tugas. |
| Pembelajaran | Pengguna dapat mengamati alasan paket diterima/ditolak beserta rule dan jalurnya. |
| Profesional | Pengguna dapat menyusun dan menguji rules secara cepat melalui GUI/CLI subset. |
| Maintainability | Engine memiliki pengujian, model state tunggal, serta dokumentasi perubahan. |

## 3. Persona dan Pengalaman Pengguna

| Persona | Kebutuhan | Pendekatan UI |
|---|---|---|
| Mahasiswa/peserta praktikum | Memahami sebab-akibat konfigurasi | Learning Mode: petunjuk, istilah, langkah evaluasi |
| Tutor/instruktur | Mendemonstrasikan ACL dan skenario | Scenario presets dan replay paket |
| Network engineer pemula | Mencoba rules tanpa hafal sintaks | GUI dan validasi input |
| Network engineer berpengalaman | Eksperimen cepat dan keterlacakan keputusan | Professional Mode: tabel rules, CLI, logs |
| Peminat NOC/SOC | Mengenal event dan alert | Monitoring simulasi dan Security Alert Center |

Learning Mode dan Professional Mode hanya mengubah penyajian/panduan. Keduanya memakai state, rules, dan hasil engine yang sama. Berpindah mode tidak menghapus konfigurasi.

## 4. Prinsip Produk dan Batasan

- **Correctness before spectacle:** keputusan firewall harus akurat sebelum efek visual.
- **Single source of truth:** CLI, GUI, 2D, 3D, log, dan alert membaca konfigurasi/hasil yang sama.
- **No misleading claims:** ACCEPT bukan jaminan koneksi aplikasi berhasil; routing dan kondisi host tetap relevan.
- Tidak menyamakan Cisco ACL dengan MikroTik Filter Rules; perilaku chain dan default policy dinyatakan eksplisit.
- Desain custom yang profesional dan mudah dipahami, bukan dashboard AI generik atau Streamlit default.
- MVP mendukung topologi kecil dan terbatas, bukan emulasi protokol jaringan lengkap.

## 5. Ruang Lingkup dan Prioritas

| Prioritas | Cakupan |
|---|---|
| **P0 (Core, wajib MVP akademik)** | Device & interface model; validasi IP; rule engine ordered; packet test; penjelasan hasil; log; UI Streamlit |
| **P1 (Differentiator)** | GUI firewall; CLI subset; 2D topology sederhana; alert event DROP; 3D sederhana jika stabil; (setelah MVP: replay visual lebih halus) |
| **P2 (Advanced, setelah MVP/stretch)** | Editor drag-and-drop penuh; model 3D realistis; threshold/watchlist; ekspor; routing kompleks; lebih banyak perangkat |

**Gate rilis:** jika fitur P1 tidak stabil mendekati deadline, kirim P0 yang berfungsi dan dokumentasikan keterbatasan. Tidak boleh menyatakan fitur P2 sudah diimplementasikan.

## 6. Keputusan Arsitektur

### ADR-001: Hybrid 2D/3D (DISETUJUI)

Workspace 2D dipakai untuk menyusun topologi, menghubungkan perangkat, memilih interface, dan membuka konfigurasi. Workspace 3D dipakai untuk melihat representasi perangkat, jalur paket, hasil ACCEPT/DROP, serta alert. Keduanya tidak memiliki mesin atau konfigurasi terpisah.

### 6.1 Workspace 2D
- Katalog perangkat: PC, router/firewall, switch, server.
- Tambah, hapus, pilih, beri nama, dan hubungkan perangkat melalui interface yang tersedia.
- Panel detail menampilkan IP/subnet/gateway, interface, dan konfigurasi firewall.
- MVP boleh memakai penempatan node otomatis atau editor koneksi berbasis pilihan; drag-and-drop bebas bukan syarat P0.

### 6.2 Workspace 3D
- Tampilan tiga dimensi berbasis koordinat dengan label dan jalur antarperangkat; representasi perangkat boleh berupa bentuk sederhana.
- Orbit/zoom sesuai dukungan renderer; pilih perangkat untuk melihat detail bila feasible.
- Replay paket berdasarkan event trace dari engine: DROP berhenti di firewall, ACCEPT meneruskan paket pada jalur yang tervalidasi.
- Tampilkan sumber/tujuan, matched rule, status dan alasan. Gunakan teks/ikon selain warna.
- MVP tidak menjanjikan model fisik vendor yang realistis atau animasi real-time yang sangat halus.

### 6.3 Strategi rendering
Python Streamlit menjadi host UI dan Python sebagai simulation engine. Plotly 2D/3D dipilih sebagai kandidat awal untuk topologi dan representasi jalur. Jika pengujian membuktikan interaksi/model 3D tidak memadai, gunakan komponen HTML/JavaScript tertanam yang terisolasi, tanpa mengganti engine Python. Perubahan renderer harus dicatat sebagai ADR baru. Jangan mengandalkan CSS untuk mengganti struktur internal Streamlit yang tidak stabil.

## 7. Persyaratan Fungsional

### FR-01: Device Library dan Topology Builder
- Perangkat memiliki ID unik, tipe, nama, daftar interface, dan atribut konfigurasi.
- Link menghubungkan dua interface yang valid; tidak boleh menghubungkan interface ke dirinya sendiri.
- Validasi nama/ID unik, IP valid, IP duplikat pada domain jaringan yang relevan, subnet dan interface.
- Satu router/firewall sebagai pusat filtering pada MVP; switch dimodelkan sebagai perangkat Layer 2 sederhana.
- Simpan dan muat skenario jaringan menggunakan JSON bila penyimpanan diimplementasikan.

### FR-02: Device & IP Configuration
- Ubah alamat IPv4, prefix/subnet, status interface, dan default gateway host.
- Tampilkan alasan kesalahan input; konfigurasi tidak valid tidak boleh diam-diam disimpan.
- Pisahkan IP interface router dari IP host; verifikasi subnet dan jalur logis sebelum uji paket.
- Perubahan konfigurasi menghasilkan `config_revision` agar riwayat simulasi tidak disalahartikan sebagai kondisi terbaru.

### FR-03: Firewall/ACL Rule Manager
Model aturan kanonik: `rule_id`, order/priority, enabled, chain/context, ingress/egress bila relevan, source CIDR, destination CIDR, protocol, source/destination port opsional, action, comment, dan counter. Evaluasi berurutan berdasarkan rule aktif; **first matching terminal action wins**.

- Chain MikroTik-style: `input` untuk paket menuju router; `forward` untuk paket yang melewati router; `output` untuk paket yang berasal dari router.
- ACCEPT mengizinkan paket melanjutkan pemrosesan; DROP membuang paket tanpa respons penolakan khusus. REJECT adalah pengembangan, bukan wajib MVP.
- Cisco-style ACL adalah model konsep/CLI subset yang diterjemahkan ke aturan kanonik dengan konteks penerapan yang jelas. Jangan mengklaim kompatibilitas penuh Cisco IOS atau MikroTik RouterOS.
- Untuk MVP, tentukan **explicit default policy per chain** dan tampilkan kepada pengguna. Preset dapat mengajarkan implicit deny Cisco sebagai skenario tersendiri. Jangan menerapkan implicit deny Cisco secara global ke semua chain MikroTik.

### FR-04: Dual CLI & GUI Configuration
- GUI Winbox-inspired: daftar filter rules, urutan, enable/disable, chain, source/destination, protocol, port, action, komentar.
- CLI Packet Tracer-inspired: prompt dan parser Python untuk perintah yang didokumentasikan (help, show, konfigurasi interface, pembuatan/penghapusan rule/ACL subset).
- Kedua jalur memanggil service konfigurasi yang sama; perubahan muncul konsisten setelah refresh/rerun.
- Perintah tidak dikenal atau tidak didukung menghasilkan error jelas; tidak dieksekusi pada OS/router sungguhan.
- Audit perubahan konfigurasi sederhana: waktu, sumber GUI/CLI, ringkasan aksi.

### FR-05: Packet Generator dan Simulation Engine
- Input: device sumber, device tujuan atau IP, protocol TCP/UDP/ICMP, port bila relevan, dan parameter uji.
- Validasi alamat dan jalur, identifikasi chain, cari rule pertama yang cocok, tentukan keputusan.
- Hasil dibedakan: `ACCEPT`, `DROP`, `NO_ROUTE`, `INVALID_CONFIG`, `UNSUPPORTED_CASE`.
- Hasil memuat trace per langkah: perangkat/link yang dilalui, evaluasi rule, alasan keputusan, timestamp, dan `config_revision`.
- ACCEPT berarti lolos kebijakan pada model simulasi; bukan bukti service tujuan aktif.

### FR-06: Logs, Monitoring, dan Analytics
- Traffic log menyimpan event ID, waktu, sumber/tujuan, protocol/port, hasil, matched rule, dan alasan.
- Dashboard menampilkan total pengujian, allow, drop, gagal rute, dan daftar kejadian terbaru.
- Filter sederhana berdasarkan keputusan/IP/waktu jika tersedia; data contoh harus diberi label simulasi.
- Tidak mengklaim membaca traffic live atau menampilkan bandwidth nyata.

### FR-07: Security Alert Center
- Setiap DROP dapat menghasilkan firewall event; notifikasi yang menonjol dapat dikonfigurasi sebagai security alert.
- Tampilkan IP sumber/tujuan, port/protocol, waktu, rule pemicu, perangkat, dan alasan.
- Alert tidak otomatis berarti serangan: penolakan dapat merupakan perilaku kebijakan yang normal.
- P2: trusted IP, watchlist, ambang penolakan berulang, deduplikasi, severity, acknowledge.
- Jangan membuat alarm audio berulang secara default; berikan kontrol pengguna jika nanti ditambahkan.

### FR-08: Learning/Professional Mode dan Scenario Lab
- Learning Mode: penjelasan chain, action, urutan rule, dan langkah keputusan paket.
- Professional Mode: tampilan ringkas, akses cepat rule table, CLI, hasil, dan log.
- Preset skenario minimal: PC diizinkan ke web server, PC diblokir SSH, aturan bertabrakan, dan salah subnet/gateway.
- Kedua mode tidak memodifikasi engine atau policy tanpa aksi konfigurasi eksplisit.

## 8. Alur Pengguna End-to-End

**Build → Configure → Simulate → Visualize → Analyze.**
Pengguna membuat perangkat/link di 2D; mengatur IP dan ACL lewat GUI/CLI; menjalankan paket virtual; melihat replay 3D; kemudian memeriksa matched rule, log, dan alert. Uji baru menggunakan konfigurasi terkini; uji lama menyimpan `config_revision`.

## 9. Model Data dan Kontrak Antarmodul

| Entitas | Atribut minimum |
|---|---|
| Device | id, name, type, interfaces |
| Interface | id, device_id, name, ipv4_cidr, enabled |
| Link | id, interface_a, interface_b, enabled |
| FirewallRule | id, order, enabled, chain, src_cidr, dst_cidr, protocol, ports, action, comment |
| PacketTest | id, source, destination, protocol, ports, timestamp, config_revision |
| SimulationResult | test_id, decision, reason, matched_rule_id, trace[] |
| SecurityEvent | id, test_id, event_type, severity, timestamp, acknowledged |
| ProjectState | devices[], links[], rules[], config_revision, scenario_metadata |

**Kontrak inti:**
- `validate_topology(state)` → errors
- `update_config(state, command)` → new_state / errors
- `simulate_packet(state, packet)` → immutable result/trace
- `derive_alerts(result, policy)` → events

Renderer tidak boleh mengubah keputusan hasil engine.

## 10. Nonfunctional Requirements

- **Keandalan:** engine deterministik untuk input dan state yang sama; semua keputusan inti dapat diuji tanpa UI.
- **Kinerja:** skenario kecil (hingga 10 perangkat dan puluhan rules) harus responsif pada laptop standar; angka final diuji, bukan dijanjikan tanpa benchmark.
- **Keamanan:** CLI adalah parser terbatas; tidak memakai `eval`, `exec`, atau shell execution dari input pengguna.
- **Privasi:** data simulasi disimpan lokal/session kecuali pengguna memilih ekspor; jangan meminta kredensial router sungguhan.
- **Usability:** label jelas, validasi inline, empty/error states, warna dengan padanan teks/ikon.
- **Portabilitas:** dependency dipin pada requirements; jalankan lokal melalui `streamlit run app.py`.
- **Aksesibilitas:** kontras layak, navigasi dasar keyboard, ukuran teks terbaca, opsi mengurangi animasi bila tersedia.

## 11. UI/UX Design System dan Halaman

Identitas: professional engineering tool + interactive learning lab. Visual minimal, terstruktur, dan berkarakter; bukan dashboard AI generik. Palet awal (dapat direvisi): base `#111827`, surface `#1E293B`, accent `#3B82F6`, allow `#16A34A`, deny `#DC2626`. Warna hanya pendukung, tidak menggantikan label. Gunakan tipografi mudah dibaca, grid dan spacing konsisten, serta ikon fungsional.

| Halaman / area | Komponen inti | Kriteria UX |
|---|---|---|
| Overview | Dashboard, status skenario, metrics, recent logs/alerts | Informasi ringkas, navigasi jelas |
| Network Workspace 2D | Device library, graph, inspector, connections | Topologi menjadi fokus utama |
| Device Configuration | Interface/IP form, validasi, CLI/GUI toggle | Perubahan dan error transparan |
| Firewall Rules | Ordered table, rule editor, action, enable/disable | Urutan evaluasi mudah dipahami |
| Packet Simulation | Packet generator, run/replay, explanation | Hasil tidak ambigu |
| 3D Visualization | Perangkat, link, packet trace, status | Sesuai engine dan tetap terbaca |
| Security Alert Center | Event list, detail, severity/status | Membedakan event dari ancaman |
| Learning Lab | Preset skenario, guided explanation | Dapat dipakai tutor/praktikan |

Evaluasi desain: hierarchy, clarity, consistency, interaction feedback, responsiveness, performance, dan kesesuaian hasil simulasi. Referensi UI sebagai inspirasi, bukan disalin mentah.

## 12. Acceptance Criteria dan Test Plan

| ID | Skenario | Hasil wajib |
|---|---|---|
| T01 | PC A → server cocok ACCEPT | Decision ACCEPT, rule tercatat |
| T02 | PC B → server cocok DROP | Decision DROP, event/log muncul |
| T03 | Dua rule cocok berurutan | Rule pertama aktif menentukan hasil |
| T04 | Rule disabled | Rule diabaikan |
| T05 | IP perangkat diubah | Uji berikutnya memakai IP terbaru |
| T06 | CLI menambah rule | GUI membaca rule yang sama |
| T07 | GUI mengubah rule | CLI `show` dan engine memakai nilai baru |
| T08 | Paket tidak memiliki jalur | NO_ROUTE, bukan DROP palsu |
| T09 | IP/prefix tidak valid | Pesan error, state tidak rusak |
| T10 | DROP pada firewall | Replay 3D berhenti di firewall |
| T11 | Pergantian Learning/Professional | State konfigurasi tidak berubah |
| T12 | Event DROP normal | Tidak otomatis diberi label serangan |
| T13 | Riwayat setelah perubahan config | Result lama menyimpan `config_revision` |
| T14 | Perintah CLI tidak dikenal | Error aman tanpa shell execution |

## 13. Roadmap dan Milestone

| Periode target | Milestone | Exit criteria |
|---|---|---|
| 24–27 Okt 2026 | PRD, UX flow, data model, proof-of-concept 3D | Keputusan teknis tercatat |
| 28 Okt–2 Nov | Engine perangkat/IP/ACL/packet + unit tests | T01–T05, T08–T09 lolos |
| 3–8 Nov | Streamlit UI, GUI/CLI subset, 2D, 3D sederhana | T06–T07, T10 lolos |
| 9–10 Nov | Logs, alerts, learning mode, integrasi | T11–T13 lolos |
| 11–13 Nov | Regression testing, polishing, laporan tugas | Demo stabil, laporan siap dikumpulkan |

Deadline akademik: 14 November 2026 pukul 00.00. Karena tenggat adalah awal hari, target aman adalah menyelesaikan pengumpulan paling lambat **13 November 2026**. Laporan maksimum 10 halaman A4 termasuk sampul/lampiran, dengan format penamaan dan tautan pengumpulan sesuai petunjuk dosen.

## 14. Risiko, Dependensi, dan Mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| 3D terlalu kompleks | MVP terlambat | Mulai proof-of-concept, gunakan bentuk sederhana |
| CLI/GUI berbeda state | Konfigurasi inkonsisten | Satu service/model konfigurasi |
| Cisco/MikroTik tercampur | Keputusan firewall keliru | Dokumentasikan semantik dan policy eksplisit |
| Streamlit rerun memutus animasi | Replay tidak stabil | Event trace immutable, kontrol replay sederhana |
| Scope creep | Core tidak selesai | P0/P1/P2, freeze menjelang deadline |
| CSS/komponen rapuh | UI rusak saat update | Versi dependency dipin, pengujian UI |
| Alert berlebihan | Pengguna bingung | Event vs alert, threshold P2 |

## 15. Pengelolaan Perubahan dan AI Handoff

PRD adalah living document. Setiap perubahan fitur dicatat dengan ID, alasan, prioritas, dampak pada data/engine/UI, acceptance criteria, dan status: Proposed → Approved → In Progress → Implemented / Deferred. Perubahan besar yang mengubah arsitektur memperbarui ADR.

- Sebelum mengubah kode, baca `docs/PRD.md`, `docs/PROJECT_CONTEXT.md`, dan struktur repository terbaru.
- Jelaskan modul yang terpengaruh dan rencana perubahan sebelum implementasi.
- Berikan path file yang dibuat/diubah, kode lengkap jika diminta, dan langkah menjalankan/mengetes.
- Jangan mengganti desain, state schema, atau semantik rule tanpa persetujuan dan catatan perubahan.
- Jalankan unit dan regression tests; update `docs/CHANGELOG.md` serta `docs/PROJECT_CONTEXT.md`.
- Jangan mengklaim fitur berhasil jika belum diuji atau hanya berupa mockup.

## 16. Keputusan Final dan Hal yang Belum Dikunci

| Aspek | Status |
|---|---|
| Tema dan platform Python Streamlit | FINAL |
| Target dua kelompok pengguna (Learning + Professional) | FINAL |
| Hybrid 2D/3D, satu state dan satu engine | FINAL (ADR-001) |
| GUI Winbox-inspired dan CLI Cisco-inspired subset | FINAL sebagai konsep; grammar dirinci saat desain teknis |
| ACL/Firewall rule engine + logs + alerts | FINAL sebagai requirement |
| Nama merek produk selain Firewall Simulator | OPEN, tidak menghambat MVP |
| Renderer 3D detail dan level animasi | OPEN, putuskan setelah proof-of-concept |
| Jumlah perangkat/link maksimum | OPEN, tentukan dari benchmark |
| Persistensi JSON vs SQLite | OPEN, JSON cukup untuk awal |

## 17. Definition of Done dan Checklist Rilis

- [ ] Aplikasi berjalan dengan instruksi instalasi dan requirements yang dapat direproduksi.
- [ ] Pengguna dapat membuat/memilih topologi, mengatur IP dan rules, serta menguji paket.
- [ ] Keputusan engine dan penjelasan matched rule konsisten di GUI, CLI, log, dan visualisasi.
- [ ] Kasus ACCEPT, DROP, NO_ROUTE, dan input tidak valid diuji.
- [ ] Notifikasi tidak salah mengartikan semua DROP sebagai serangan.
- [ ] Fitur yang belum selesai dinyatakan jelas sebagai limitation/backlog.
- [ ] Dokumen PRD, context, changelog, dan laporan akademik diperbarui.
- [ ] Demo akhir tidak bergantung pada perangkat jaringan fisik atau koneksi internet.

## 18. Catatan Referensi Akademik

Batasan akademik merujuk pada berkas PetunjukTugas.pdf: tema Firewall Simulator, Python Streamlit, laporan maksimal 10 halaman, tenggat 14 November 2026 pukul 00.00. Berkas contoh laporan hanya referensi organisasi laporan, bukan sumber persyaratan fungsional. Spesifikasi teknis lain dalam PRD adalah keputusan desain proyek yang perlu diuji selama implementasi.

*End of PRD v1.0. Revisi berikutnya menggunakan v1.1 dan changelog.*