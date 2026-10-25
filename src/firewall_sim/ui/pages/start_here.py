"""Halaman orientasi dan panduan awal pengguna: Mulai di Sini."""

from __future__ import annotations

import streamlit as st

from firewall_sim.core.validation import validate_topology
from firewall_sim.ui.components import page_header, render_simulation_banner
from firewall_sim.ui.state import (
    clear_simulation_data,
    get_security_events,
    get_simulation_history,
    get_state,
    get_traffic_logs,
    load_demo_scenario,
    reset_to_preset,
)


def render_start_here_page() -> None:
    """Merender halaman beranda dan panduan alur kerja Firewall Simulator."""
    render_simulation_banner()
    page_header(
        title="Mulai di Sini",
        description="Pusat orientasi untuk memahami cara kerja simulator firewall virtual langkah demi langkah.",
    )

    state = get_state()
    validation_errors = validate_topology(state)
    is_valid = (len(validation_errors) == 0)
    sim_history = get_simulation_history()
    traffic_logs = get_traffic_logs()
    alerts = get_security_events()

    # Hero Section
    with st.container(border=True):
        st.markdown(
            "### :material/explore: Selamat Datang di Firewall Simulator Virtual\n\n"
            "Simulator ini dirancang untuk memvisualisasikan bagaimana firewall berbasis tabel "
            "(stateful/packet filtering) memproses, mengevaluasi aturan secara berurutan (*first matching terminal action wins*), "
            "dan menentukan nasib paket jaringan melintasi interface router. "
            "Anda dapat memuat skenario demo siap pakai atau memulai dari lab kosong."
        )

        col_btn1, col_btn2, _ = st.columns([1.5, 1.5, 2])
        with col_btn1:
            if st.button("🚀 Muat Demo Siap Pakai", key="btn_demo_load", type="primary", use_container_width=True):
                ok, errs = load_demo_scenario()
                if ok:
                    st.toast("Demo siap pakai berhasil dimuat! Cek hasil di Aturan, 3D, dan Log.")
                    st.rerun()
                else:
                    st.error(f"Gagal memuat demo: {errs}")
        with col_btn2:
            if st.button("📁 Mulai dari Proyek Kosong", key="btn_empty_start", use_container_width=True):
                reset_to_preset("empty")
                clear_simulation_data()
                st.toast("Proyek kosong siap dikonfigurasi.")
                st.rerun()

    # Stepper 5 Langkah Horizontal
    st.markdown("#### :material/linear_scale: Alur Kerja 5 Langkah")

    step_cols = st.columns(5)

    # 1. Build
    with step_cols[0]:
        with st.container(border=True):
            st.markdown("**1. Build**")
            st.caption("Topologi Jaringan")
            if not is_valid:
                st.badge("Perlu Perhatian", icon=":material/warning:", color="orange")
            elif len(state.devices) >= 3:
                st.badge("Selesai", icon=":material/check_circle:", color="green")
            else:
                st.badge("Belum", icon=":material/radio_button_unchecked:", color="gray")

            st.caption(f"{len(state.devices)} perangkat")
            if st.button("Buka Topologi", key="step_open_network", use_container_width=True):
                st.session_state["nav_page"] = "network"
                st.rerun()

    # 2. Configure
    with step_cols[1]:
        with st.container(border=True):
            st.markdown("**2. Configure**")
            st.caption("Aturan Firewall")
            if len(state.rules) > 0:
                st.badge("Selesai", icon=":material/check_circle:", color="green")
            else:
                st.badge("Belum", icon=":material/radio_button_unchecked:", color="gray")

            st.caption(f"{len(state.rules)} aturan aktif")
            if st.button("Buka Aturan", key="step_open_rules", use_container_width=True):
                st.session_state["nav_page"] = "rules"
                st.rerun()

    # 3. Simulate
    with step_cols[2]:
        with st.container(border=True):
            st.markdown("**3. Simulate**")
            st.caption("Uji Paket Virtual")
            if len(sim_history) > 0:
                st.badge("Selesai", icon=":material/check_circle:", color="green")
            else:
                st.badge("Belum", icon=":material/radio_button_unchecked:", color="gray")

            st.caption(f"{len(sim_history)} pengujian")
            if st.button("Buka Simulasi", key="step_open_packet_sim", use_container_width=True):
                st.session_state["nav_page"] = "packet_sim"
                st.rerun()

    # 4. Visualize
    with step_cols[3]:
        with st.container(border=True):
            st.markdown("**4. Visualize**")
            st.caption("Visualisasi 3D")
            if len(sim_history) > 0:
                st.badge("Selesai", icon=":material/check_circle:", color="green")
            else:
                st.badge("Belum", icon=":material/radio_button_unchecked:", color="gray")

            st.caption("Replay jalur 3D")
            if st.button("Buka 3D", key="step_open_viz3d", use_container_width=True):
                st.session_state["nav_page"] = "viz3d"
                st.rerun()

    # 5. Analyze
    with step_cols[4]:
        with st.container(border=True):
            st.markdown("**5. Analyze**")
            st.caption("Log & Peringatan")
            if len(traffic_logs) > 0 or len(alerts) > 0:
                st.badge("Selesai", icon=":material/check_circle:", color="green")
            else:
                st.badge("Belum", icon=":material/radio_button_unchecked:", color="gray")

            st.caption(f"{len(traffic_logs)} log | {len(alerts)} alert")
            if st.button("Buka Analisis", key="step_open_traffic_logs", use_container_width=True):
                st.session_state["nav_page"] = "traffic_logs"
                st.rerun()

    # Kartu Alur Singkat (3 kalimat) & Panduan Konsep
    col_flow, col_guide = st.columns([3, 2])
    with col_flow:
        with st.container(border=True):
            st.markdown("#### :material/route: Alur Singkat")
            st.markdown(
                "1. **Rancang dan Hubungkan**: Buat topologi perangkat host, switch, dan router firewall dengan alokasi IP yang valid.\n"
                "2. **Terapkan Kebijakan**: Susun daftar aturan firewall secara terurut pada chain `FORWARD`, `INPUT`, atau `OUTPUT` dengan aksi terminal `ACCEPT` atau `DROP`.\n"
                "3. **Uji dan Analisis**: Kirim paket virtual, pantau pergerakannya secara visual pada model 3D, lalu periksa rincian log trafik serta peringatan keamanan."
            )

    with col_guide:
        with st.container(border=True):
            st.markdown("#### :material/lightbulb: Tips Penting")
            st.markdown(
                "- **First Matching Rule Wins**: Firewall memeriksa aturan dari nomor terkecil ke terbesar. Begitu cocok, evaluasi berhenti.\n"
                "- **Default Policy**: Jika tidak ada aturan yang cocok, paket mengikuti *default policy* chain yang bersangkutan.\n"
                "- **Same-Subnet Bypass**: Lalu lintas antar-host dalam subnet yang sama melalui switch tidak melewati firewall router."
            )
