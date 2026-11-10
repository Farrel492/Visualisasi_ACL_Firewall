"""Lab Belajar: skenario terpandu. Muat skenario, jalankan uji, dan lihat apakah hasilnya sesuai target."""

from __future__ import annotations

from typing import Optional

import streamlit as st

from firewall_sim.core.models import Decision, SimulationResult
from firewall_sim.core.simulator import simulate_packet
from firewall_sim.scenarios.presets import ScenarioInfo, list_scenarios
from firewall_sim.ui.components import (
    next_steps,
    page_header,
    render_simulation_banner,
    render_workflow_rail,
)
from firewall_sim.ui.labels import decision_style, friendly_text
from firewall_sim.ui.state import (
    add_simulation_run,
    get_state,
    load_scenario_state,
    set_nav_page,
)

KEY_LAB_RESULT = "fw_sim_lab_result"


def evaluate(sc: ScenarioInfo, res: SimulationResult) -> bool:
    """Skenario lulus bila keputusan engine sama dengan target skenario."""
    return res.decision == sc.expected_decision


def run_scenario(sc: ScenarioInfo, load: bool = True) -> Optional[SimulationResult]:
    """Muat skenario ke workspace (menggantikan topologi) lalu jalankan paket ujinya."""
    new_state = sc.factory()
    load_scenario_state(new_state)
    if not load:
        return None
    res = simulate_packet(new_state, sc.test_packet)
    add_simulation_run(sc.test_packet, res)
    st.session_state[KEY_LAB_RESULT] = {"id": sc.id, "decision": res.decision.value, "reason": res.reason, "passed": evaluate(sc, res)}
    return res


def _result_block(state, sc: ScenarioInfo) -> None:
    saved = st.session_state.get(KEY_LAB_RESULT)
    if not saved or saved.get("id") != sc.id:
        return
    decision = Decision(saved["decision"])
    led, _, text_color = decision_style(decision)
    st.markdown(
        f'<div translate="no"><span class="fw-led {led}"></span>Hasil uji: '
        f'<b style="color:{text_color};font-family:var(--fw-mono)">{decision.value}</b>. '
        f"{friendly_text(state, saved['reason'])}</div>",
        unsafe_allow_html=True,
    )
    if saved["passed"]:
        st.success(f"Lulus: hasilnya sesuai target skenario ({sc.expected_decision.value}).", icon=":material/check_circle:")
    else:
        st.warning(
            f"Belum sesuai: hasil {decision.value}, target {sc.expected_decision.value}.",
            icon=":material/warning:",
        )
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Lihat di Topologi 2D", key=f"lab_go_net_{sc.id}", width="stretch"):
            set_nav_page("network")
            st.rerun()
    with c2:
        if st.button("Lihat di 3D", key=f"lab_go_3d_{sc.id}", width="stretch"):
            st.session_state["sel_viz3d_test"] = 0
            set_nav_page("viz3d")
            st.rerun()
    with c3:
        if st.button("Lihat aturan", key=f"lab_go_rules_{sc.id}", width="stretch"):
            set_nav_page("firewall_rules")
            st.rerun()


def render_learning_lab_page() -> None:
    render_simulation_banner()
    page_header(
        title="Lab Belajar",
        description="Skenario siap pakai: muat, jalankan uji, dan cek apakah hasilnya sesuai target.",
    )
    render_workflow_rail("learning_lab")

    scenarios = list_scenarios()
    state = get_state()
    active_id = dict(state.scenario_metadata).get("id")

    col_main, col_side = st.columns([2.6, 1.0], gap="medium")
    with col_main:
        st.caption("Memuat skenario mengganti topologi dan aturan di workspace saat ini, dan membersihkan hasil uji lama.")
        for sc in scenarios:
            is_active = active_id == sc.id
            with st.container(border=True):
                st.markdown(f"**{sc.title}**" + ("  (aktif)" if is_active else ""))
                st.write(sc.objective)
                with st.expander("Langkah belajar", expanded=False):
                    for idx, step in enumerate(sc.steps, 1):
                        st.markdown(f"{idx}. {step}")
                st.caption(f"Hasil yang diharapkan: {sc.expected_decision.value}. {sc.expected_result}")
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("Muat dan uji", icon=":material/play_arrow:", key=f"load_{sc.id}", type="primary", width="stretch"):
                        run_scenario(sc, load=True)
                        st.toast(f"Skenario '{sc.title}' dimuat dan diuji.")
                        st.rerun()
                with b2:
                    if st.button("Muat saja", icon=":material/download:", key=f"load_only_{sc.id}", width="stretch"):
                        run_scenario(sc, load=False)
                        st.session_state.pop(KEY_LAB_RESULT, None)
                        st.toast(f"Skenario '{sc.title}' dimuat.")
                        st.rerun()
                _result_block(state, sc)

    with col_side:
        with st.expander("Tips belajar", expanded=False):
            st.markdown(
                "- Setiap skenario memuat topologi dan aturan untuk satu kasus.\n"
                "- Amati pengaruh urutan aturan dan gateway pada keputusan.\n"
                "- Gunakan 3D untuk melihat di mana paket diizinkan atau berhenti."
            )
        next_steps([
            ("Tinjau di Topologi 2D", "network"),
            ("Periksa Aturan Firewall", "firewall_rules"),
            ("Lihat Replay 3D", "viz3d"),
            ("Buka Log Trafik", "traffic_logs"),
        ])
