# ADR-003: Identitas Visual "Meja Lab Jaringan"

**Status:** diterima.

**Konteks.** Tampilan awal berupa Streamlit bawaan (palet slate-biru, kartu seragam) dan dinilai seperti template buatan AI.

**Keputusan.** Area kerja terang dan tenang; topologi 2D, 3D, dan terminal berupa "layar instrumen" gelap. Token ada di `ui/theme.py` dan `.streamlit/config.toml`: meja `#E6E9EC`, panel `#F4F5F6`, tinta `#18222B`, aksen `#16808D`, layar `#1E252B`, LED hijau/merah/amber (varian teks yang lulus kontras). Font IBM Plex Sans dan Mono (OFL) dilayani lokal dari `static/fonts/`. Navigasi berupa rail kiri tetap (ikon saja saat diciutkan). Status memakai titik LED ditambah istilah teknis, bukan hanya warna. Tanpa emoji, gradient, atau bayangan.

**Konsekuensi.** Warna dasar dan aksen menyimpang dari palet PRD bagian 11; makna hijau/merah/amber untuk ACCEPT/DROP/NO_ROUTE dipertahankan. PRD tidak diubah.
