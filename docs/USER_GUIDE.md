# Panduan Pengguna Firewall Simulator (User Guide)

Selamat datang di **Firewall Simulator Virtual**. Dokumen ini dirancang sebagai panduan lengkap bagi pengguna baru dan evaluator akademik untuk mengoperasikan simulator jaringan, memahami mekanisme evaluasi firewall, menjalankan pengujian paket, serta melakukan pemecahan masalah (troubleshooting).

---

## 1. Alur Kerja Utama 5 Langkah

Firewall Simulator dirancang dengan alur kerja logis 5 tahap:

```
[1. Build] ➔ [2. Configure] ➔ [3. Simulate] ➔ [4. Visualize] ➔ [5. Analyze]
 Topologi     Aturan Firewall   Kirim Paket      Replay 3D       Log & Alert
```

1. **Langkah 1 - Build (Topologi Jaringan 2D)**:
   - Akses menu **Topologi 2D** pada grup navigasi *Bangun & Konfigurasi*.
   - Rancang topologi perangkat (Host PC, Switch L2, Router Firewall, dan Web Server).
   - Hubungkan kabel virtual antar-interface perangkat.
2. **Langkah 2 - Configure (Alamat IP & Aturan Firewall)**:
   - Buka menu **Konfigurasi Perangkat**: tetapkan alamat IPv4 CIDR dan default gateway pada host.
   - Buka menu **Aturan Firewall**: susun aturan filtering berurutan pada chain `FORWARD`, `INPUT`, atau `OUTPUT`, serta tentukan aksi `ACCEPT` atau `DROP`.
3. **Langkah 3 - Simulate (Inisiasi Uji Paket Virtual)**:
   - Buka menu **Simulasi Paket**.
   - Tentukan perangkat sumber, tujuan (IP/perangkat), protokol (TCP/UDP/ICMP), dan port tujuan.
   - Klik **Jalankan Simulasi Paket** atau gunakan tombol **Uji Cepat**.
4. **Langkah 4 - Visualize (Penelusuran Jalur 3D)**:
   - Buka menu **Visualisasi 3D**.
   - Amati pergerakan paket virtual frame-demi-frame melintasi lapisan topologi menggunakan slider atau tombol navigasi. Paket yang terkena `DROP` akan berhenti di router.
5. **Langkah 5 - Analyze (Log Trafik & Pusat Peringatan)**:
   - Periksa **Log Trafik** untuk rekapitulasi tabular seluruh pengujian paket.
   - Buka **Pusat Peringatan (Alert Center)** untuk meninjau rekaman event penolakan firewall.

---

## 2. Skrip Demonstrasi 10 Menit

Gunakan skrip terstruktur ini saat presentasi atau demonstrasi langsung:

| Menit | Menu / Aksi yang Dilakukan | Ekspektasi Hasil Visual |
|---|---|---|
| **00:00 - 02:00** | Buka **Mulai di Sini**, klik tombol **"🚀 Muat Demo Siap Pakai"**. | Topologi standar dimuat, 2 aturan firewall terkonfigurasi, dan 2 pengujian otomatis selesai. Indikator stepper 5 kartu berubah menjadi **Selesai (Hijau)**. |
| **02:00 - 04:00** | Buka menu **Topologi 2D**. Amati tata letak graf berlapis (PC di kiri, switch, router di tengah-kanan, server di kanan). Klik salah satu node untuk inspeksi. | Graf interaktif Plotly 520px tampil rapi dengan chip legenda. Inspector di bawah grafik menampilkan interface dan gateway aktif. |
| **04:00 - 06:00** | Buka menu **Aturan Firewall**. Amati daftar aturan pada tab `Chain FORWARD`. Tunjukkan tombol naik/turun order dan status aktif. | Terlihat Rule #1 (ACCEPT PC A ke Server Port 80) dan Rule #2 (DROP PC B ke Server Port 80). Banner penegasan *First Match Wins* terlihat jelas. |
| **06:00 - 08:00** | Buka menu **Simulasi Paket**. Klik tombol uji cepat **"PC A ➔ Server :80"** lalu **"PC B ➔ Server :80"**. | Muncul kartu hasil beraksen: PC A berstatus **ACCEPT (Hijau)**, sedangkan PC B berstatus **DROP (Merah)** lengkap dengan alasan penolakan dan trace bernomor. |
| **08:00 - 10:00** | Klik tombol **"🧊 Lihat di 3D"** pada hasil DROP, amati bahwa titik paket berhenti di router. Buka **Pusat Peringatan** untuk melihat event DROP tercatat tanpa label serangan palsu. | Replay 3D menunjukkan paket berhenti di router (Z=0). Dasbor Peringatan memuat catatan resmi penolakan kebijakan. |

---

## 3. Daftar Perintah CLI (Cisco-Inspired Subset)

Aplikasi menyediakan **Konsol Terminal CLI** yang aman dan terisolasi tanpa eksekusi shell sistem:

| Perintah CLI | Contoh Penggunaan | Deskripsi & Kegunaan |
|---|---|---|
| `help` | `help` | Menampilkan ringkasan sintaks dan daftar perintah CLI yang didukung. |
| `show running-config` | `show running-config` | Menampilkan seluruh konfigurasi aktif: perangkat, link, interface, dan rule. |
| `show interfaces` | `show interfaces` | Menampilkan daftar seluruh interface perangkat beserta alamat IP dan statusnya. |
| `show rules` | `show rules` | Menampilkan tabel aturan firewall berurutan per chain. |
| `rule add` | `rule add chain=forward proto=tcp dport=80 action=accept` | Menambahkan aturan firewall baru pada chain tertentu. |
| `policy set` | `policy set chain=forward action=drop` | Mengubah kebijakan default (*default policy*) untuk chain tertentu. |
| `test` | `test source=pc_a destination=server proto=tcp dport=80` | Mengeksekusi pengujian transmisi paket virtual langsung dari baris perintah. |

---

## 4. Glosarium Istilah Teknis

- **Chain**: Jalur traversal paket di firewall:
  - `INPUT`: Paket yang ditujukan langsung ke alamat IP router/firewall itu sendiri.
  - `FORWARD`: Paket yang melintasi router dari satu subnet asal menuju subnet tujuan lain.
  - `OUTPUT`: Paket yang diinisiasi langsung oleh router menuju jaringan luar.
- **ACCEPT**: Keputusan firewall yang mengizinkan paket lewat menuju tujuan. *(Catatan: lolos kebijakan simulasi bukan jaminan service port tujuan aktif).*
- **DROP**: Keputusan firewall yang menolak dan membuang paket secara diam-diam tanpa balasan ICMP unreachable.
- **NO_ROUTE**: Status kegagalan perutean di mana gateway atau interface tujuan tidak dapat dijangkau oleh rute L2/L3. *(Bukan penolakan firewall).*
- **Default Policy**: Aksi cadangan yang diterapkan jika paket dievaluasi hingga aturan terakhir pada chain namun tidak ada yang cocok.
- **Config Revision**: Nomor revisi atomik bertambah satu setiap kali konfigurasi topologi atau aturan berubah, menjamin audit jejak yang akurat.
- **First Matching Terminal Action Wins**: Prinsip evaluasi terurut dari atas ke bawah; aturan pertama yang cocok langsung mengeksekusi aksinya dan evaluasi berhenti.

---

## 5. Pertanyaan Umum & Diagnostik Masalah (FAQ)

### Mengapa hasil pengujian paket saya menghasilkan status `NO_ROUTE` dan bukan `DROP`?
`NO_ROUTE` berarti paket tidak menemukan jalur fisik atau logis menuju subnet tujuan (misalnya host belum memiliki default gateway, gateway berada di subnet yang salah, atau link kabel virtual terputus). Simulator membedakan secara tegas antara masalah perutean jaringan (`NO_ROUTE`) dan penolakan kebijakan firewall (`DROP`).

### Mengapa lalu lintas antar PC A dan PC B tidak melewati firewall?
PC A dan PC B berada pada subnet yang sama (`192.168.1.0/24`) dan terhubung melalui Switch LAN (Layer 2). Berdasarkan standar arsitektur TCP/IP (*Same-Subnet Bypass*), lalu lintas lokal antar-host diteruskan langsung pada Layer 2 dan tidak dialihkan ke router gateway, sehingga tidak diproses oleh firewall router.

### Apakah status ACCEPT menjamin server web dapat diakses secara nyata?
Tidak. Seluruh aktivitas dalam aplikasi adalah **SIMULASI VIRTUAL**. Status ACCEPT hanya membuktikan bahwa paket lolos aturan filter firewall; aplikasi tidak membuka soket jaringan fisik ke perangkat keras produksi.
