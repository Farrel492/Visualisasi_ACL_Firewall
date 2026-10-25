# ADR-001: Hybrid 2D/3D Workspace

- **Status:** Accepted
- **Tanggal:** 2026-10-24

## Konteks
Produk perlu menyusun topologi dengan mudah dan sekaligus memvisualisasikan jalur paket secara intuitif, tanpa membuat dua sumber kebenaran.

## Keputusan
- Workspace **2D** untuk menyusun topologi, menghubungkan perangkat, memilih interface, dan membuka konfigurasi.
- Workspace **3D** untuk representasi perangkat, jalur paket, hasil ACCEPT/DROP, dan alert.
- Keduanya memakai **satu state (ProjectState) dan satu engine**. Renderer tidak boleh mengubah keputusan engine.
- Renderer awal: Plotly 2D/3D di dalam Streamlit.

## Konsekuensi
- Jika Plotly terbukti tidak memadai, boleh memakai komponen HTML/JS tertanam yang terisolasi, tanpa mengganti engine Python. Perubahan itu wajib dicatat sebagai ADR baru (mis. ADR-002).
- Replay 3D dibangun dari event trace immutable, sehingga tahan terhadap rerun Streamlit.
- Tidak ada janji model fisik vendor yang realistis atau animasi real-time sangat halus pada MVP.