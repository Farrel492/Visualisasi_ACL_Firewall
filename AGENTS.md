# AGENTS.md: aturan kerja untuk AI agent

Proyek: Firewall Simulator (Python + Streamlit). Spesifikasi lengkap ada di `docs/PRD.md`.

## Wajib sebelum mengubah kode
1. Baca `docs/PRD.md`, `docs/PROJECT_CONTEXT.md`, dan struktur repository terbaru.
2. Jelaskan modul yang terpengaruh dan rencana perubahan sebelum implementasi.

## Aturan arsitektur
- Engine (`src/firewall_sim/core/`) murni Python: tidak boleh mengimpor Streamlit atau library UI.
- Satu source of truth: GUI, CLI, 2D, 3D, log, dan alert membaca state/hasil yang sama.
- Semua perubahan konfigurasi lewat `config/service.py`; GUI dan CLI tidak boleh memodifikasi state langsung.
- `SimulationResult` immutable. Renderer tidak boleh mengubah keputusan engine.
- Evaluasi rule: berurutan, hanya rule enabled, first matching terminal action wins. Default policy eksplisit per chain. Jangan menerapkan implicit deny Cisco secara global.
- Hasil simulasi dibedakan: ACCEPT, DROP, NO_ROUTE, INVALID_CONFIG, UNSUPPORTED_CASE. NO_ROUTE tidak boleh dilaporkan sebagai DROP.
- Setiap perubahan konfigurasi menaikkan `config_revision`; hasil lama menyimpan revision-nya.

## Keamanan
- Parser CLI terbatas. Dilarang `eval`, `exec`, `os.system`, `subprocess` terhadap input pengguna.
- Perintah tidak dikenal menghasilkan error yang jelas.

## Larangan
- Jangan mengganti desain, state schema, atau semantik rule tanpa persetujuan eksplisit dan catatan di CHANGELOG.
- Jangan mengklaim fitur berhasil jika belum diuji atau hanya mockup.
- Jangan mengklaim fitur P2 sudah diimplementasikan.
- Jangan menyatakan setiap DROP sebagai serangan.
- Jangan membuat UI yang bergantung pada CSS untuk mengubah struktur internal Streamlit.

## Setelah setiap perubahan
- Jalankan `pytest` dan laporkan hasil sebenarnya.
- Update `docs/CHANGELOG.md` dan `docs/PROJECT_CONTEXT.md`.
- Laporkan path file yang dibuat/diubah dan cara menjalankan/mengetes.

## Konvensi
- Python 3.10+, type hints, docstring singkat.
- Dependency dipin di `requirements.txt`.
- Bahasa UI: Indonesia, kecuali istilah teknis (ACCEPT, DROP, chain, dll).