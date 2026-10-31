"""Visualisasi 3D: scene Three.js dengan model perangkat dan replay paket.

Kontrol putar/zoom/geser dan Maju/Mundur/Putar ada di dalam komponen (tanpa rerun),
jadi tombolnya selalu responsif. Keputusan tetap berasal dari engine Python.
"""

from __future__ import annotations

import streamlit as st

from firewall_sim.core.models import Decision
from firewall_sim.ui import topo
from firewall_sim.ui.components import (
    empty_state,
    next_steps,
    page_header,
    render_flow_next,
    render_simulation_banner,
    render_workflow_rail,
)
from firewall_sim.ui.state import (
    get_cables,
    get_layout,
    get_selected_device,
    get_simulation_history,
    get_state,
)
from firewall_sim.ui.theme import get_decision_badge
from firewall_sim.ui.widgets import apply_component_event, scene3d_view


def render_viz3d_page() -> None:
    render_simulation_banner()
    page_header(
        title="Visualisasi 3D",
        description="Putar, perbesar, dan geser perangkat; jalankan replay untuk melihat paket bergerak.",
    )
    render_workflow_rail("viz3d")

    state = get_state()
    history = get_simulation_history()

    if not state.devices:
        empty_state(
            message="Belum ada perangkat dalam topologi. Buat perangkat di Topologi 2D terlebih dahulu.",
            action_label="Buka Topologi 2D",
            target_page_or_callback="network",
            key="empty_viz3d_dev_btn",
            icon=":material/view_in_ar:",
        )
        return

    selected_res = None
    if history:
        options = {
            idx: f"{item.timestamp.strftime('%H:%M:%S')}  {get_decision_badge(item.decision)}  ({item.test_id})"
            for idx, item in enumerate(history)
        }
        sel_idx = st.selectbox(
            "Hasil uji yang diputar",
            options=list(options.keys()),
            index=0,
            format_func=lambda x: options[x],
            key="sel_viz3d_test",
            help="Secara default hasil uji terbaru. Jalankan uji baru di Simulasi Paket.",
        )
        selected_res = history[sel_idx]

    layout = topo.resolve_layout(state, get_layout())
    payload = topo.component_payload(
        state, layout, get_cables(), selected_res, get_selected_device(), editable=True
    )

    col_view, col_info = st.columns([3.1, 1.0], gap="medium")
    with col_view:
        event = scene3d_view(payload, key="viz3d_scene")
        if apply_component_event(event, "viz3d_scene"):
            st.rerun()
        if not history:
            st.caption("Belum ada hasil uji. Anda tetap bisa memutar kamera dan memindahkan perangkat.")

    with col_info:
        if selected_res is None:
            empty_state(
                message="Belum ada pengujian paket untuk diputar.",
                action_label="Buka Simulasi Paket",
                target_page_or_callback="packet_sim",
                key="empty_viz3d_hist_btn",
                icon=":material/send:",
            )
        else:
            with st.container(border=True):
                st.markdown("**Keputusan simulasi**")
                st.markdown(get_decision_badge(selected_res.decision))
                st.caption(selected_res.reason)
                if selected_res.matched_rule_id:
                    st.markdown(f"Rule cocok: `{selected_res.matched_rule_id}`")
                if selected_res.decision == Decision.DROP:
                    st.caption("DROP berhenti di router; paket tidak diteruskan ke subnet tujuan.")
                if selected_res.config_revision != state.config_revision:
                    st.warning("Konfigurasi sudah berubah sejak uji ini.", icon=":material/history:")
        next_steps([("Buka Log Trafik", "traffic_logs"), ("Jalankan Uji Lain", "packet_sim")])

    render_flow_next("traffic_logs", "Log Trafik", "Analisis riwayat dan statistik paket yang disimulasikan.")
