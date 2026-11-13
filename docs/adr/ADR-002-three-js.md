# ADR-002: Three.js untuk Visualisasi 3D

**Status:** diterima.

**Konteks.** Plotly `Scatter3d` hanya menampilkan titik dan tidak dapat menggambar model perangkat atau menganimasikan paket. Pengguna meminta perangkat 3D yang mirip aslinya.

**Keputusan.** Memakai Three.js 0.160.1 (lisensi MIT) beserta `OrbitControls`, dibundel lokal di `src/firewall_sim/ui/frontend/scene3d/vendor/` dan dimuat lewat import map. Komponen berupa halaman HTML mandiri (`declare_component` dengan folder lokal) yang berbicara dengan Streamlit lewat `postMessage`. Model perangkat dibangun secara prosedural (tanpa berkas glTF). Tombol replay (Maju, Mundur, Putar) berada di dalam komponen sehingga tidak memicu rerun.

**Konsekuensi.**
- Tanpa CDN: berjalan offline saat demo.
- Keputusan tetap berasal dari engine Python; viewer hanya menampilkan data replay.
- Butuh WebGL; bila gagal, viewer menampilkan pesan.
- Isi WebGL tidak dapat diuji AppTest; diverifikasi lewat browser.
