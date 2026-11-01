"""Halaman orientasi dan panduan awal pengguna: Mulai di Sini."""

from __future__ import annotations

import streamlit as st

from firewall_sim.core.models import Decision
from firewall_sim.core.validation import validate_topology
from firewall_sim.ui.components import page_header, render_simulation_banner
from firewall_sim.ui.state import (
    get_security_events,
    get_simulation_history,
    get_state,
    get_traffic_logs,
    load_demo_scenario,
    set_nav_page,
)


def render_start_here_page() -> None:
    """Merender halaman orientasi awal Firewall Simulator."""
    render_simulation_banner()
    page_header(
        title="Mulai di Sini",
        description="Simulator firewall jaringan virtual: rancang topologi, susun filter paket, dan amati traversal rule.",
    )

    state = get_state()
    validation_errors = validate_topology(state)
    is_valid = len(validation_errors) == 0
    sim_history = get_simulation_history()
    traffic_logs = get_traffic_logs()
    alerts = get_security_events()

    # Hitung rekomendasi langkah berikutnya dari state
    has_devices = len(state.devices) > 0
    has_rules = len(state.rules) > 0
    has_tests = len(sim_history) > 0
    has_drop = any(r.decision == Decision.DROP for r in sim_history)

    # Aplikasi selalu dimulai dengan topologi bawaan (perangkat sudah ada, rule belum),
    # jadi kondisi awal ditentukan oleh rule dan hasil uji, bukan oleh jumlah perangkat.
    if not has_rules and not has_tests:
        btn_label = "Muat demo siap pakai"
        btn_target = "load_demo"
        next_hint = (
            "Topologi bawaan sudah ada. Muat demo untuk mendapat dua aturan dan dua hasil uji contoh, "
            "atau susun aturan sendiri."
        )
    elif not has_tests:
        btn_label = "Jalankan uji paket"
        btn_target = "packet_sim"
        next_hint = "Aturan firewall sudah ada. Uji bagaimana paket diperlakukan."
    elif has_drop:
        btn_label = "Coba matikan aturan DROP lalu uji ulang"
        btn_target = "firewall_rules"
        next_hint = "Ada paket yang ditolak (DROP). Matikan aturannya, lalu uji ulang dan bandingkan hasilnya."
    else:
        btn_label = "Lihat jalur paket di 3D"
        btn_target = "viz3d"
        next_hint = "Paket berhasil lolos. Amati jalurnya di panggung 3D."

    with st.container(border=True):
        st.markdown("#### Langkah berikutnya")
        st.caption(next_hint)
        if st.button(btn_label, type="primary", key="btn_next_action", width="stretch"):
            if btn_target == "load_demo":
                ok, errs = load_demo_scenario()
                if ok:
                    st.toast("Demo siap pakai berhasil dimuat!")
                    st.rerun()
                else:
                    st.error(f"Gagal memuat demo: {errs}")
            else:
                set_nav_page(btn_target)
                st.rerun()
        if btn_target == "load_demo":
            if st.button("Atur aturan sendiri", key="btn_manual_rules", width="stretch"):
                set_nav_page("firewall_rules")
                st.rerun()

    # 5 Langkah sebagai baris teks berstatus
    st.markdown("##### Alur Kerja 5 Langkah")

    status_build = "Siap" if (is_valid and len(state.devices) >= 3) else ("Perlu cek" if not is_valid else "Kosong")
    status_cfg = "Siap" if len(state.rules) > 0 else "Kosong"
    status_sim = "Selesai" if len(sim_history) > 0 else "Belum uji"
    status_viz = "Siap" if len(sim_history) > 0 else "Belum ada data"
    status_ana = "Ada log" if (len(traffic_logs) > 0 or len(alerts) > 0) else "Kosong"

    steps_data = [
        ("Bangun", status_build, "Rancang topologi perangkat dan pengkabelan jaringan virtual."),
        ("Konfigurasi", status_cfg, "Tentukan aturan filter paket berurutan serta kebijakan default per chain."),
        ("Simulasi", status_sim, "Injeksi paket uji untuk memverifikasi evaluasi rule firewall."),
        ("Visualisasi", status_viz, "Amati pergerakan traversal paket dan titik evaluasi dalam panggung 3D."),
        ("Analisis", status_ana, "Periksa catatan log trafik dan telaah insiden keamanan jaringan."),
    ]

    for name, status, desc in steps_data:
        st.markdown(f"- **{name}** ({status}): {desc}")

    with st.expander(":material/school: Panduan Konsep & Tips Belajar Firewall", expanded=False):
        col_flow, col_guide = st.columns([3, 2])
        with col_flow:
            st.markdown(
                "**Prinsip Kerja Firewall:**\n"
                "1. **Alur Evaluasi Berurutan**: Rule dievaluasi dari nomor urut terendah (paling atas). Rule pertama yang cocok langsung dieksekusi.\n"
                "2. **Aksi Terminal**: Aksi `ACCEPT` atau `DROP` mengakhiri evaluasi paket seketika.\n"
                "3. **Default Policy**: Menentukan nasib paket bila seluruh rule aktif tidak ada yang cocok."
            )
        with col_guide:
            st.markdown(
                "**Karakteristik Topologi:**\n"
                "- **Same-Subnet Bypass**: Komunikasi antar-host pada switch L2 yang sama tidak melewati router firewall.\n"
                "- **Chain**: `FORWARD` untuk lalu lintas antar-subnet; `INPUT` untuk paket yang ditujukan langsung ke IP router."
            )
