# Firewall Simulator

Aplikasi simulasi firewall/ACL interaktif berbasis Python Streamlit: topologi 2D, visualisasi paket 3D, log, dan alert. Semua aktivitas adalah simulasi, bukan trafik jaringan nyata.

## Menjalankan

    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    streamlit run app.py

## Menguji

    pytest

## Fitur Utama
1. **Hybrid 2D/3D Workspace**:
   - Workspace 2D untuk penyusunan topologi, inspeksi interface, dan koneksi link.
   - Visualisasi 3D (Plotly Scatter3d) dengan pemutaran trace paket langkah-demi-langkah (slider/prev-next) tahan rerun; paket DROP berhenti di firewall router (T10).
2. **Learning & Professional Mode**:
   - Mode switcher interaktif di sidebar.
   - *Learning Mode*: Panel penjelasan konsep firewall (chain, rule order, first match wins, implicit deny vs default policy).
   - *Professional Mode*: Tampilan ringkas terpadu.
3. **Traffic Logs & Monitoring**:
   - Agregasi statistik metrik (total, ACCEPT, DROP, NO_ROUTE).
   - Filter data berdasarkan keputusan, alamat IP/perangkat, dan rentang waktu.
4. **Security Alert Center**:
   - Deteksi dan ringkasan event penolakan paket (DROP).
   - Teks panduan permanen: penolakan paket adalah perilaku kebijakan normal, bukan otomatis serangan.
5. **Learning Lab (Guided Scenarios)**:
   - 4 skenario praktik terpadu: Web Allow (HTTP), SSH Blocked (Policy DROP), Colliding Rules (First Match Wins), dan Wrong Subnet/Gateway (NO_ROUTE).
   - Tombol muat skenario dan eksekusi uji otomatis.
6. **JSON Storage & Persistence**:
   - Simpan dan muat proyek dalam format JSON terstruktur lengkap dengan verifikasi `schema_version` dan validasi topologi.
7. **CLI Console**:
   - Terminal parser aman berbasis `shlex` (tanpa eval/exec/subprocess).

## Perintah CLI (Cisco/Packet Tracer Inspired Subset)
Aplikasi menyediakan terminal CLI interaktif dengan tata bahasa berikut:
- `help` : Menampilkan bantuan.
- `show <running-config|interfaces|rules [chain]|policy|audit|revision|links>` : Menampilkan status dan konfigurasi.
- `interface <device> <ifname> ip address <ip> <prefix|netmask>` : Mengatur IP interface.
- `interface <device> <ifname> <shutdown|no shutdown>` : Mengatur status interface.
- `gateway <host> <ip>` : Mengatur default gateway host.
- `rule add chain=<input|forward|output> [src=..] [dst=..] [proto=..] [sport=..] [dport=..] action=<accept|drop> [comment=".."]` : Menambah aturan firewall.
- `rule remove <id> | rule enable <id> | rule disable <id> | rule move <id> <order>` : Manajemen aturan firewall.
- `policy <chain> <accept|drop>` : Mengatur default policy per chain.
- `access-list <permit|deny> <proto> <src|any> <dst|any> [eq <port>]` : Translasi ACL ke aturan kanonik chain forward.
- `test <src_device> <dst_device_or_ip> <tcp|udp|icmp> [port]` : Simulasi paket virtual via CLI.

## Diagnostik Browser & Pengaturan Toolbar
- **Terjemahan Otomatis Browser**: Harap nonaktifkan fitur terjemahan otomatis peramban (seperti Google Translate / Edge Translate) untuk alamat `localhost`. Modifikasi DOM teks oleh ekstensi terjemahan peramban pada elemen React Streamlit dapat memicu galat runtime peramban `NotFoundError: Failed to execute 'removeChild' on 'Node'`.
- **Mode Toolbar Pengembang**: Toolbar bawaan Streamlit secara default diatur ke `toolbarMode = "minimal"` pada `.streamlit/config.toml` guna menyembunyikan tombol Deploy dan menu bawaan yang mengganggu presentasi. Jika Anda memerlukan menu developer saat debugging lokal, ubah menjadi `toolbarMode = "developer"`.

## Dokumentasi Lengkap
- `docs/UI_AUDIT.md`: Laporan audit antarmuka, reproduksi error topologi, dan matriks fungsionalitas
- `docs/USER_GUIDE.md`: Panduan pengguna, alur kerja, skrip demo 10 menit, dan glosarium
- `docs/TEST_REPORT.md`: Laporan pengujian kriteria penerimaan T01-T14 & benchmark kinerja
- `docs/PRD.md`: Spesifikasi produk
- `docs/PROJECT_CONTEXT.md`: Status proyek terkini
- `docs/CHANGELOG.md`: Riwayat perubahan
- `docs/adr/`: Keputusan arsitektur
- `AGENTS.md`: Aturan untuk AI agent

## Status
Fitur MVP Lengkap, Audit & Redesain UI Tahap R1 Selesai (77 Pytest Passed, 0 Failed, Bebas Emoji, Toolbar Minimal, Sidebar SVG Logo, Form Topologi Sempurna). Lihat `docs/PROJECT_CONTEXT.md`.