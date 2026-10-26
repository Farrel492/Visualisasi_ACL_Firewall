"""Halaman orientasi dan panduan awal pengguna: Mulai di Sini."""

from __future__ import annotations

import streamlit as st

from firewall_sim.core.validation import validate_topology
from firewall_sim.ui.components import page_header, render_flow_next, render_simulation_banner
from firewall_sim.ui.state import (
    clear_simulation_data,
    get_security_events,
    get_simulation_history,
    get_state,
    get_traffic_logs,
    is_learning,
    load_demo_scenario,
    reset_to_preset,
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
    is_valid = (len(validation_errors) == 0)
    sim_history = get_simulation_history()
    traffic_logs = get_traffic_logs()
    alerts = get_security_events()

    # Hero & Aksi Cepat
    with st.container(border=True):
        st.markdown(
            "#### Simulator Firewall Berbasis Filter Paket Virtual\n"
            "Evaluasi aturan firewall dilakukan berurutan (*first matching terminal action wins*) "
            "pada chain FORWARD dan INPUT melintasi interface router. "
            "Pilih opsi di bawah untuk langsung mencoba atau merancang konfigurasi dari awal."
        )

        col_btn1, col_btn2, _ = st.columns([1.6, 1.6, 1.8])
        with col_btn1:
            if st.button("Muat Demo Siap Pakai", icon=":material/play_arrow:", key="btn_demo_load", type="primary", use_container_width=True):
                ok, errs = load_demo_scenario()
                if ok:
                    st.toast("Demo siap pakai berhasil dimuat! Lanjutkan ke Topologi atau Aturan.")
                    st.rerun()
                else:
                    st.error(f"Gagal memuat demo: {errs}")
        with col_btn2:
            if st.button("Mulai Proyek Kosong", icon=":material/note_add:", key="btn_empty_start", use_container_width=True):
                reset_to_preset("empty")
                clear_simulation_data()
                st.toast("Proyek kosong siap dikonfigurasi.")
                st.rerun()

    # Stepper 5 Langkah Terarah
    st.markdown("##### :material/linear_scale: Alur Kerja 5 Langkah")

    step_cols = st.columns(5)

    # 1. Build
    with step_cols[0]:
        with st.container(border=True):
            st.markdown("**1. Build**")
            st.caption("Topologi Jaringan")
            if not is_valid:
                st.badge("Perlu Cek", icon=":material/warning:", color="orange")
            elif len(state.devices) >= 3:
                st.badge("Siap", icon=":material/check_circle:", color="green")
            else:
                st.badge("Kosong", icon=":material/radio_button_unchecked:", color="gray")

            st.caption(f"{len(state.devices)} perangkat")
            if st.button("Topologi", icon=":material/hub:", key="step_open_network", use_container_width=True):
                st.session_state["nav_page"] = "network"
                st.rerun()

    # 2. Configure
    with step_cols[1]:
        with st.container(border=True):
            st.markdown("**2. Configure**")
            st.caption("Aturan Firewall")
            if len(state.rules) > 0:
                st.badge("Siap", icon=":material/check_circle:", color="green")
            else:
                st.badge("Kosong", icon=":material/radio_button_unchecked:", color="gray")

            st.caption(f"{len(state.rules)} aturan")
            if st.button("Aturan", icon=":material/shield:", key="step_open_rules", use_container_width=True):
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
                st.badge("Belum Uji", icon=":material/radio_button_unchecked:", color="gray")

            st.caption(f"{len(sim_history)} pengujian")
            if st.button("Simulasi", icon=":material/send:", key="step_open_packet_sim", use_container_width=True):
                st.session_state["nav_page"] = "packet_sim"
                st.rerun()

    # 4. Visualize
    with step_cols[3]:
        with st.container(border=True):
            st.markdown("**4. Visualize**")
            st.caption("Visualisasi 3D")
            if len(sim_history) > 0:
                st.badge("Siap", icon=":material/check_circle:", color="green")
            else:
                st.badge("Belum Ada Data", icon=":material/radio_button_unchecked:", color="gray")

            st.caption("Replay paket 3D")
            if st.button("Panggung 3D", icon=":material/view_in_ar:", key="step_open_viz3d", use_container_width=True):
                st.session_state["nav_page"] = "viz3d"
                st.rerun()

    # 5. Analyze
    with step_cols[4]:
        with st.container(border=True):
            st.markdown("**5. Analyze**")
            st.caption("Log & Peringatan")
            if len(traffic_logs) > 0 or len(alerts) > 0:
                st.badge("Ada Log", icon=":material/check_circle:", color="green")
            else:
                st.badge("Kosong", icon=":material/radio_button_unchecked:", color="gray")

            st.caption(f"{len(traffic_logs)} log | {len(alerts)} alert")
            if st.button("Log Trafik", icon=":material/receipt_long:", key="step_open_traffic_logs", use_container_width=True):
                st.session_state["nav_page"] = "traffic_logs"
                st.rerun()

    # Mode Edukatif: Panduan Konsep & Tips (Hanya ditampilkan jika Learning Mode aktif)
    if is_learning():
        with st.expander(":material/school: Panduan Konsep & Tips Belajar Firewall", expanded=True):
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

    render_flow_next("network", "Topologi 2D", "Mulai dengan meninjau atau menambah perangkat pada topologi.")

