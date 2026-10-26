"""Learning Lab and guided scenario presets page."""

from __future__ import annotations

import streamlit as st

from firewall_sim.core.simulator import simulate_packet
from firewall_sim.scenarios.presets import list_scenarios
from firewall_sim.ui.components import (
    next_steps,
    page_header,
    render_simulation_banner,
)
from firewall_sim.ui.state import (
    add_simulation_run,
    get_state,
    set_project_state,
)
from firewall_sim.ui.theme import get_decision_badge


def render_learning_lab_page() -> None:
    """Merender halaman skenario praktik terpandu Learning Lab."""
    render_simulation_banner()
    page_header(
        title="Lab Belajar",
        description="Eksplorasi konsep aturan firewall, urutan filter, dan diagnostik rute jaringan melalui skenario terpandu.",
    )

    scenarios = list_scenarios()
    curr_state = get_state()
    curr_scen_id = dict(curr_state.scenario_metadata).get("id")

    col_main, col_side = st.columns([2.2, 1.0])

    with col_main:
        st.markdown("#### :material/menu_book: Katalog Skenario Praktik")

        for sc in scenarios:
            is_active = (curr_scen_id == sc.id)
            active_badge = " -> [AKTIF DI WORKSPACE]" if is_active else ""

            with st.container(border=True):
                st.markdown(f"### {sc.title}{active_badge}")
                st.markdown(f"**Tujuan Praktik:**\n\n{sc.objective}")

                with st.expander(":material/format_list_numbered: Langkah-langkah Pembelajaran", expanded=False):
                    for idx, step in enumerate(sc.steps, 1):
                        st.markdown(f"{idx}. {step}")

                st.markdown(f"**Hasil yang Diharapkan:** `{sc.expected_decision.value}` — *{sc.expected_result}*")

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("Muat ke Workspace", icon=":material/download:", key=f"load_{sc.id}", type="primary" if is_active else "secondary", use_container_width=True):
                        new_state = sc.factory()
                        set_project_state(new_state)
                        st.toast(f"Skenario '{sc.title}' berhasil dimuat!")
                        st.rerun()

                with col_btn2:
                    if st.button("Jalankan Uji Langsung", icon=":material/play_arrow:", key=f"run_{sc.id}", use_container_width=True):
                        sim_state = sc.factory() if not is_active else curr_state
                        res = simulate_packet(sim_state, sc.test_packet)
                        add_simulation_run(sc.test_packet, res)

                        st.markdown("---")
                        st.markdown(f"**Hasil Keputusan:** {get_decision_badge(res.decision)}")
                        st.caption(f"Alasan: {res.reason}")

                        if res.decision == sc.expected_decision:
                            st.success(
                                f"Hasil pengujian SESUAI dengan target skenario ({sc.expected_decision.value})!",
                                icon=":material/check_circle:",
                            )
                        else:
                            st.warning(
                                f"Hasil pengujian ({res.decision.value}) berbeda dari target ({sc.expected_decision.value}).",
                                icon=":material/warning:",
                            )

    with col_side:
        # Panduan & Langkah Berikutnya
        with st.container(border=True):
            st.markdown("#### :material/tips_and_updates: Tips Belajar")
            st.markdown(
                "- Setiap skenario memuat konfigurasi topologi dan rule yang telah dirancang untuk mendemonstrasikan kasus nyata.\n"
                "- Amati pengaruh rule order dan subnet gateway pada keputusan akhir.\n"
                "- Gunakan visualisasi 3D untuk melihat titik di mana paket diizinkan atau dihentikan."
            )

        next_steps([
            ("Tinjau di Topologi 2D", "network"),
            ("Periksa Aturan Firewall", "firewall_rules"),
            ("Lihat Replay 3D", "viz3d"),
            ("Buka Log Trafik", "traffic_logs"),
        ])
