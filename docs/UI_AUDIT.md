# Audit Antarmuka Pengguna & Fungsionalitas (UI Audit)

Dokumen ini mendokumentasikan hasil audit teknis mendalam terhadap 11 halaman antarmuka Firewall Simulator, pengujian reproduksi bug menggunakan `streamlit.testing.v1.AppTest`, pesan error riil yang ditemukan, perbaikan fungsional, dan matriks interaktivitas.

---

## 1. Reproduksi Error Topologi (R1.8)

Pengujian reproduksi dilakukan langsung terhadap alur mutasi state `ConfigService` dan interaksi `network.py`.

| Aksi Topologi | Pesan Error Asli / Kondisi Riil | Akar Masalah | Solusi & Hasil Perbaikan |
|---|---|---|---|
| **Tambah Perangkat** | `[HOST_MISSING_IP] Host 'PC C' wajib memiliki IP pada interface 'eth0'.`<br>`[HOST_MISSING_GATEWAY] Host 'PC C' wajib memiliki default gateway.` | Form sebelumnya hanya menerima `name` dan `type` pada `AddDevice`. Ketika tipe PC atau Server dipilih, objek interface tidak membawa IP dan `default_gateway=None`. Engine memanggil `validate_topology(new_state)` saat pre-commit dan menolak perubahan karena aturan integritas host MVP mewajibkan IP CIDR dan gateway. | Form diperbarui dengan input dinamis: jika memilih PC atau Server, disediakan input IPv4 CIDR (default terisi contoh valid) dan Default Gateway. `Interface(name="eth0")` dibuat otomatis dengan status aktif. Penambahan PC/Server kini sukses tanpa exception. |
| **Hubungkan Link** | `Minimal 2 interface bebas dibutuhkan untuk membuat link baru.` (form tersembunyi) | Pada `default_lab()`, seluruh interface (PC A `if_pc_a`, PC B `if_pc_b`, Switch `sw_p1..p3`, Router `r_lan`/`r_srv`, Server `if_srv`) 100% terhubung. Total port bebas = 0. Form dropdown tidak muncul dan caption membingungkan pengguna tanpa arahan tindakan. | Pesan diperbarui secara solutif: *"Semua port terpakai; putuskan link lain atau tambah Switch untuk menghubungkan perangkat."* Saat Switch baru atau perangkat baru ditambahkan, form langsung terbuka dan menampilkan pilihan interface bebas. |
| **Hapus Link** | Dropdown hanya menampilkan ID mentah string seperti `link_pca_sw`. | Tidak ada `format_func` yang memetakan ID link ke nama perangkat dan antarmuka ujung-ke-ujung. | Ditambahkan formatter ramah: `link_pca_sw: PC A (if_pc_a) <-> Switch LAN (sw_p1)`. Eksekusi `RemoveLink` sukses memutus link dan membebaskan port. |
| **Hapus Perangkat** | Penghapusan router dilindungi, peringatan cascade link sebelumnya menggunakan emoji `⚠️`. | Router firewall tunggal dilindungi oleh `service.py`. | Teks diperjelas tanpa emoji; dropdown hanya menampilkan host/switch. Penghapusan perangkat sukses dan link terkait otomatis terhapus secara atomik. |

---

## 2. Audit Komponen & Interaktivitas 11 Halaman (R1.9)

Setiap elemen interaktif diuji status fungsinya (berfungsi nyata vs dekoratif).

| Halaman | Komponen / Widget | Efek yang Diharapkan | Efek Aktual | Status |
|---|---|---|---|---|
| **Mulai di Sini** | Tombol `Muat Demo Siap Pakai` | Reset ke default lab, suntik 2 rule (ACCEPT & DROP), jalankan uji simulasi otomatis, isi log dan alert. | `ProjectState` terkonfigurasi, >=2 riwayat uji, >=1 ACCEPT, >=1 DROP, >=1 alert terbentuk. | Berfungsi |
| **Mulai di Sini** | Tombol `Mulai dari Proyek Kosong` | Reset state ke proyek tanpa perangkat/link/rule. | Session state dan ProjectState bersih, empty state aktif di halaman lain. | Berfungsi |
| **Mulai di Sini** | Stepper 5 Kartu | Mengarahkan pengguna ke halaman workflow terkait (Build, Configure, Simulate, Visualize, Analyze). | Mengubah `nav_page` dan merender halaman tujuan. | Berfungsi |
| **Dasbor** | Metrik KPI (4 card) | Menampilkan ringkasan skenario, revisi, perangkat, link & rule. | Data sinkron dengan `ProjectState`. | Berfungsi |
| **Dasbor** | Validasi Topologi | Menampilkan banner kepatuhan aturan MVP / error jika ada. | Sinkron dengan hasil `validate_topology(state)`. | Berfungsi |
| **Dasbor** | Form Default Policy | Mengubah kebijakan default chain FORWARD, INPUT, OUTPUT. | Mutasi via `SetDefaultPolicy`, revisi naik +1, audit log tercatat. | Berfungsi |
| **Dasbor** | Tombol Unduh Proyek (JSON) | Mengunduh file JSON skema 1.0. | File JSON terunduh dengan struktur valid. | Berfungsi |
| **Dasbor** | Form Unggah Proyek (JSON) | Membaca file JSON dan menerapkan state baru. | Validasi skema berjalan, state terganti jika valid. | Berfungsi |
| **Dasbor** | Tombol Reset Default / Kosong | Mengembalikan workspace ke preset. | Berfungsi bersih, membersihkan log/history. | Berfungsi |
| **Topologi 2D** | Visualisasi Graf Plotly | Menampilkan node perangkat dan link koneksi. | Render graf berlapis sesuai posisi koordinat. | Berfungsi |
| **Topologi 2D** | Inspector Perangkat | Menampilkan detail IP, status interface, dan gateway. | Menampilkan detail perangkat terpilih dari dropdown. | Berfungsi |
| **Topologi 2D** | Form Kelola Topologi (4 expander) | Tambah/hapus perangkat dan link. | Mengirim command atomik ke `apply_command`. | Berfungsi |
| **Konfigurasi Perangkat** | Form Simpan Alamat IP | Mengubah IP interface host/router. | Menjalankan validasi CIDR inline, memutasi via `SetInterfaceIP`. | Berfungsi |
| **Konfigurasi Perangkat** | Tombol Toggle Status Interface | Mengaktifkan / menonaktifkan interface (Up/Down). | Memutasi via `SetInterfaceEnabled`, revisi naik +1. | Berfungsi |
| **Konfigurasi Perangkat** | Form Default Gateway | Mengubah gateway host. | Memutasi via `SetGateway`, revisi naik +1. | Berfungsi |
| **Aturan Firewall** | Form Default Policy per Chain | Mengubah default policy per chain. | Memutasi via `SetDefaultPolicy`. | Berfungsi |
| **Aturan Firewall** | Form Tambah Rule Baru | Menambahkan aturan firewall berurutan. | Memutasi via `AddRule`, urutan terurut, revisi naik +1. | Berfungsi |
| **Aturan Firewall** | Tombol Matikan / Aktifkan Rule | Toggle status rule tanpa menghapus. | Memutasi via `ToggleRule`, rule dilewati jika nonaktif. | Berfungsi |
| **Aturan Firewall** | Tombol Hapus Rule | Menghapus rule dari chain. | Memutasi via `RemoveRule`, revisi naik +1. | Berfungsi |
| **Aturan Firewall** | Tombol Naik / Turun Order | Menggeser prioritas evaluasi rule. | Memutasi via `MoveRule`, nomor urutan teratur ulang. | Berfungsi |
| **Simulasi Paket** | Tombol Uji Cepat (3 tombol) | Mengirim paket preset PC A->Server, PC B->Server, PC A->PC B. | Menjalankan simulator deterministik, mencatat trace & hasil. | Berfungsi |
| **Simulasi Paket** | Form Generator Paket Kustom | Mengirim paket dengan parameter manual. | Mengevaluasi paket terhadap firewall rules aktif. | Berfungsi |
| **Simulasi Paket** | Tombol Lihat di 3D / Lihat di Log | Navigasi cepat dari kartu hasil pengujian. | Mengarahkan `nav_page` ke halaman 3D atau Log Trafik. | Berfungsi |
| **Visualisasi 3D** | Selectbox Sesi Pengujian | Memilih riwayat pengujian untuk direplay. | Memuat frame replay paket yang sesuai. | Berfungsi |
| **Visualisasi 3D** | Slider & Tombol Prev/Next | Menelusuri pergerakan paket frame-by-frame. | State langkah tersimpan di session state tahan rerun. | Berfungsi |
| **Log Trafik** | Filter Keputusan & Pencarian IP | Menyaring tabel log berdasarkan status / IP. | Menampilkan subset log yang relevan secara real-time. | Berfungsi |
| **Pusat Peringatan** | Toggle Highlight DROP | Menyalakan penandaan otomatis event DROP. | Memperbarui `AlertPolicy.highlight_drop` di session state. | Berfungsi |
| **Lab Belajar** | Tombol Muat ke Workspace | Mengganti state dengan skenario lab terpandu. | Memuat topologi dan aturan preset skenario. | Berfungsi |
| **Lab Belajar** | Tombol Jalankan Uji Langsung | Mengeksekusi paket uji bawaan skenario. | Menguji kecocokan hasil terhadap target pembelajaran. | Berfungsi |
| **Konsol CLI** | Form Input CLI (Enter) | Menjalankan perintah konfigurasi / inspeksi. | Dievaluasi oleh `parse_and_execute`, output tercatat. | Berfungsi |
| **Konsol CLI** | Chip Contoh Perintah Cepat | Klik untuk langsung mengeksekusi perintah. | Perintah langsung terkirim dan hasilnya tampil di terminal. | Berfungsi |

---

## 3. Verifikasi Efek Lintas Halaman (Cross-Page Consistency)

- **Revisi Konfigurasi Atomik**: Setiap kali rule, IP interface, gateway, perangkat, atau link diubah, nomor revisi `config_revision` bertambah +1.
- **Pendeteksian Riwayat Usang (Stale Test Detection)**:
  - Kartu hasil simulasi paket di `packet_sim.py` secara otomatis menampilkan banner peringatan jika `item.config_revision != state.config_revision`.
  - Log analitik di `traffic_logs.py` menyimpan `config_revision` pada setiap entri untuk audit forensik.
  - Sesi 3D Replay mendeteksi perubahan topologi dan memperbarui posisi koordinat spasial.


---

## 4. Hasil Audit & Perbaikan Fase 1 (Bug Nyata & Interaktivitas Penuh)

Audit menyeluruh terhadap tombol dan formulir di seluruh 11 halaman setelah fondasi meja lab jaringan dipasang:

| Halaman | Komponen / Widget | Efek yang Diharapkan | Efek Aktual Setelah Perbaikan | Status |
|---|---|---|---|---|
| **Lab Belajar** | Tombol `Muat ke Workspace` | Memuat state skenario, pindah ke halaman topologi (`network`), dan menampilkan toast konfirmasi. | State skenario terpasang, navigasi otomatis berpindah ke `network`, toast berhasil dimunculkan. | **Diperbaiki (B1)** |
| **Konsol CLI** | Chip perintah `test` & Referensi Sintaks | Menjalankan simulasi paket virtual dengan parameter valid tanpa parsing error. | Sintaks diperbarui dari `source=...` menjadi `test <src> <dst> <proto> [port]` (mis. `test pc_a server tcp 80`); 100% chip valid dieksekusi parser. | **Diperbaiki (B2)** |
| **Simulasi Paket** | Tombol `Hapus riwayat uji` | Menghapus riwayat hasil uji simulasi paket dengan dialog konfirmasi modal (`st.dialog`). | Dialog modal konfirmasi muncul; saat disetujui, memanggil `clear_test_history()` tanpa menyentuh log/alert. | **Ditambahkan (B3)** |
| **Log Trafik** | Tombol `Kosongkan log` | Mengosongkan seluruh riwayat log trafik dengan dialog konfirmasi modal (`st.dialog`). | Dialog modal konfirmasi muncul; saat disetujui, memanggil `clear_traffic_logs()`. | **Ditambahkan (B3)** |
| **Pusat Peringatan** | Tombol `Kosongkan peringatan` | Mengosongkan daftar event peringatan keamanan dengan dialog konfirmasi modal (`st.dialog`). | Dialog modal konfirmasi muncul; saat disetujui, memanggil `clear_security_events()`. | **Ditambahkan (B3)** |
| **Konsol CLI** | Tombol `Bersihkan layar` | Menghapus riwayat input/output terminal pada layar dengan dialog konfirmasi modal (`st.dialog`). | Dialog modal konfirmasi muncul; saat disetujui, memanggil `clear_cli_history()`. | **Ditambahkan (B3)** |
| **Dasbor** | Tombol `Proyek baru` | Membuat workspace baru dengan token unik via `new_workspace()` setelah konfirmasi dialog modal. | Dialog modal konfirmasi muncul; saat disetujui, token baru dibuat dan state diinisialisasi bersih. | **Ditambahkan (B5)** |
| **Dasbor** | Tombol `Ekspor proyek (JSON)` | Mengunduh berkas konfigurasi proyek JSON yang valid sesuai skema. | Berkas JSON berhasil diunduh dengan penamaan `firewall_project_rev<rev>.json`. | **Disesuaikan (B5)** |
| **Dasbor** | Expander `Impor proyek` | Membaca dan memvalidasi berkas JSON proyek, lalu menerapkannya ke session state. | Berkas divalidasi skema dan integritasnya; bila valid, state dimuat dan halaman diperbarui. | **Disesuaikan (B5)** |
| **Mulai di Sini** | Tombol `Langkah berikutnya` | Menghitung rekomendasi tindakan tunggal secara cerdas berdasarkan state aktual. | 5 kondisi dinamis (0 dev, 0 rule, 0 test, has DROP, all ACCEPT) mengarahkan pengguna ke aksi relevan. | **Diperbaiki (B1/B3)** |
