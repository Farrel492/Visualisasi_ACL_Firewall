# Panduan Pengguna Firewall Simulator

## Apa yang dilakukan aplikasi ini

Aplikasi menjawab satu pertanyaan: **kenapa sebuah paket diterima atau ditolak firewall?** Bayangkan satpam gerbang dengan daftar aturan. Setiap tamu (paket) diperiksa, daftar dibaca dari atas ke bawah, dan **aturan pertama yang cocok menang**. Jika tidak ada yang cocok, berlaku aturan umum (*default policy*). Semua berupa simulasi.

## Alur 5 langkah

| Langkah | Halaman | Tujuan |
|---|---|---|
| 1. Build | Topologi 2D | Susun perangkat dan kabel |
| 2. Configure | Konfigurasi Perangkat, Aturan Firewall | Atur IP, gateway, dan aturan |
| 3. Simulate | Simulasi Paket | Kirim paket uji |
| 4. Visualize | Visualisasi 3D | Lihat jalur paket |
| 5. Analyze | Log Trafik, Pusat Peringatan | Tinjau riwayat dan penolakan |

Halaman **Mulai di Sini** selalu menampilkan satu tombol "Langkah berikutnya" yang menyesuaikan kondisi proyek.

## Skrip demo 10 menit

1. **Mulai di Sini**: klik **Muat demo siap pakai**. Terisi 5 perangkat, 2 aturan, dan 2 hasil uji.
2. **Topologi 2D**: lihat jaringannya (PC A, PC B, Switch LAN, Router Firewall, Web Server). Seret satu perangkat; posisinya tersimpan.
3. **Aturan Firewall**: dua aturan di chain FORWARD: PC A ke Web Server port 80 ACCEPT, PC B ke Web Server port 80 DROP. Perhatikan kolom Status ("aktif") dan urutan nomor.
4. **Simulasi Paket**: klik **PC B ke Web Server, HTTP 80**. Kartu hasil menyebut "DROP oleh aturan #2, chain FORWARD". Tekan **Putar paket** pada topologi di bawahnya.
5. **Visualisasi 3D**: pilih hasil uji, tekan **Putar paket**; paket berhenti di router.
6. **Eksperimen inti**: kembali ke **Aturan Firewall**, pilih aturan #2, klik **Matikan**, lalu uji ulang PC B. Hasilnya berubah menjadi ACCEPT dan **Revisi konfigurasi** (rail kiri bawah) naik. Hasil lama diberi label "Konfigurasi sudah berubah".
7. **Log Trafik** dan **Pusat Peringatan**: lihat catatan tiap uji. Peringatan DROP dapat ditandai **sudah ditinjau**.
8. **Konsol CLI**: lihat bagian CLI di bawah.

## Halaman

- **Dasbor**: ringkasan status, tabel uji terbaru, dan Manajemen Proyek (**Proyek baru**, **Ekspor proyek (JSON)**, **Impor proyek**, **Reset Topologi**).
- **Topologi 2D**: panel "Kelola topologi": *Tambah perangkat*, *Hubungkan dengan kabel* (pilih jenis kabel FastEthernet atau Serial, lalu port bebas), *Hapus perangkat atau link*, *Reset posisi perangkat*. Klik perangkat untuk melihat port dan koneksinya.
- **Konfigurasi Perangkat**: IP interface, status port, default gateway. Topologi kecil di samping form; klik perangkat untuk memilihnya. IP tidak valid ditolak dan tidak tersimpan.
- **Aturan Firewall**: kebijakan default per chain, tabel aturan per chain, **Naik/Turun/Matikan/Hapus**, dan form **Tambah aturan** (pilih perangkat sebagai sumber/tujuan atau CIDR manual).
- **Simulasi Paket**: **Uji cepat** dan **Paket kustom** (tujuan perangkat atau IP manual). Hasil: kalimat ringkas, alasan, aturan penentu, jalur bernomor, topologi dengan replay, **Lihat di 3D**, **Lihat di Log**, **Hapus riwayat**.
- **Visualisasi 3D**: putar (seret latar), zoom (gulir), geser (klik kanan), pindahkan perangkat (seret perangkat). Tombol **Putar paket**, **Maju**, **Mundur**, **Reset kamera**.
- **Log Trafik**: filter keputusan dan pencarian (boleh nama perangkat), **Kosongkan log**.
- **Pusat Peringatan**: peringatan dari paket DROP. DROP adalah perilaku normal kebijakan, bukan otomatis serangan.
- **Lab Belajar**: skenario terpandu. **Muat dan uji** memuat skenario, menjalankan uji, dan menampilkan Lulus atau Belum sesuai target. **Muat saja** hanya memuat skenario.

## Konsol CLI

Pilih perangkat pada kotak "Perangkat yang dikonfigurasi". Ketik perintah lalu Enter, atau klik chip "Perintah cepat". Ketik `?` untuk bantuan sesuai mode. Singkatan didukung (`conf t`, `sh run`, `int fa0/1`).

**Router dan switch (gaya Cisco IOS)**

| Mode | Prompt | Masuk dengan |
|---|---|---|
| user | `Router-Firewall>` | awal |
| privileged | `Router-Firewall#` | `enable` |
| config | `Router-Firewall(config)#` | `configure terminal` |
| config-if | `Router-Firewall(config-if)#` | `interface fa0/1` |

Perintah: `enable`, `disable`, `configure terminal`, `interface <nama>`, `ip address <ip> <netmask>`, `no ip address`, `shutdown`, `no shutdown`, `hostname <nama>`, `exit`, `end`, `ping <perangkat|ip>`, `show running-config`, `show ip interface brief`, `show interfaces`, `show rules`, `show policy`, `show links`, `show revision`, `show audit`, `test <asal> <tujuan> <tcp|udp|icmp> [port]`. Dari mode config juga tersedia `rule add chain=forward proto=tcp dport=80 action=accept`, `policy forward drop`, dan `access-list permit tcp any any eq 80`.

**PC dan server (gaya Windows)**: prompt `C:\>`; perintah `ipconfig`, `ipconfig set <ip> <netmask> <gateway>`, `ping <perangkat|ip>`.

Contoh konfigurasi router:
```
enable
configure terminal
interface fa0/1
ip address 10.0.0.1 255.255.255.0
no shutdown
exit
rule add chain=forward proto=tcp dport=443 action=accept
end
show running-config
```
Catatan: ping yang berasal dari router sendiri belum didukung simulator; lakukan ping dari PC atau Server.

## Glosarium

- **Chain**: daftar aturan menurut arah paket. FORWARD = paket yang melintasi router antar subnet; INPUT = menuju router; OUTPUT = berasal dari router (belum didukung).
- **ACCEPT / DROP**: diizinkan lewat / dibuang. ACCEPT berarti lolos kebijakan simulasi, bukan bukti layanan di tujuan aktif.
- **NO_ROUTE**: paket tidak punya jalur (mis. salah subnet atau gateway), sehingga firewall belum memutuskan.
- **Default policy**: keputusan jika tidak ada aturan yang cocok.
- **First match wins**: aturan aktif pertama yang cocok menentukan hasil; aturan nonaktif dilewati.
- **Revisi konfigurasi**: nomor yang naik setiap konfigurasi berubah; hasil uji lama ditandai usang.
- **Fa / Se**: port FastEthernet / Serial; satu port hanya dapat dipakai satu kabel.

## FAQ

- **Label tombol aneh atau muncul error tampilan?** Matikan terjemahan otomatis browser untuk `localhost`.
- **Pekerjaan hilang setelah refresh?** Jangan hapus bagian `?w=...` di alamat URL; itu penanda workspace Anda. Membuka alamat tanpa itu membuat workspace baru. Gunakan **Ekspor proyek (JSON)** di Dasbor sebagai cadangan.
- **Pesan "Minimal 2 interface bebas"?** Semua port sudah terpakai. Putuskan link lain atau tambahkan perangkat.
- **3D kosong?** Browser perlu WebGL. Gunakan Chrome atau Edge terbaru.
- **Perintah CLI "tidak dikenali"?** Periksa mode prompt; `configure terminal` hanya di mode privileged (`enable` dulu). Ketik `?` untuk daftar perintah mode itu.
