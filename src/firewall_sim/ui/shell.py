"""Kerangka aplikasi: rail navigasi kiri (tetap tampil, ikon saja saat diciutkan)."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from firewall_sim.ui.state import (
    get_nav_page,
    is_rail_open,
    set_nav_page,
    toggle_rail,
)

MARK_PATH = Path(__file__).resolve().parent / "assets" / "mark.svg"

NAV_GROUPS = [
    ("Mulai", [("start_here", "Mulai di Sini", "explore"), ("overview", "Dasbor", "dashboard")]),
    (
        "Bangun",
        [
            ("network", "Topologi 2D", "hub"),
            ("device_config", "Konfigurasi Perangkat", "settings"),
            ("firewall_rules", "Aturan Firewall", "security"),
        ],
    ),
    ("Simulasi", [("packet_sim", "Simulasi Paket", "send"), ("viz3d", "Visualisasi 3D", "view_in_ar")]),
    (
        "Analisis",
        [
            ("traffic_logs", "Log Trafik", "list_alt"),
            ("alerts", "Pusat Peringatan", "notifications_active"),
            ("learning_lab", "Lab Belajar", "school"),
            ("cli_console", "Konsol CLI", "terminal"),
        ],
    ),
]

def _mark_data_uri() -> str:
    import base64

    try:
        return "data:image/svg+xml;base64," + base64.b64encode(MARK_PATH.read_bytes()).decode("ascii")
    except OSError:
        return ""


PAGE_LABELS = {pid: label for _, items in NAV_GROUPS for pid, label, _ in items}


def render_rail(state, validation_errors) -> None:
    """Gambar isi rail. Dipanggil di dalam st.container(key="fw_rail")."""
    openr = is_rail_open()
    current = get_nav_page()

    mark = _mark_data_uri()
    if openr:
        st.html(
            f'<div class="fw-brand" translate="no"><img src="{mark}" width="36" height="36" alt="">'
            "<div><b>Firewall Simulator</b><small>Lab jaringan virtual</small></div></div>"
        )
    else:
        st.html(f'<div class="fw-brand" translate="no"><img src="{mark}" width="34" height="34" alt=""></div>')

    if st.button(
        "Ciutkan menu" if openr else "\u200b",
        icon=":material/left_panel_close:" if openr else ":material/left_panel_open:",
        key="rail_toggle",
        help="Ciutkan atau lebarkan menu",
        width="stretch",
    ):
        toggle_rail()
        st.rerun()

    for group, items in NAV_GROUPS:
        if openr:
            st.html(f'<div class="fw-rail-cap" translate="no">{group}</div>')
        for page_id, label, icon in items:
            on = "on" if current == page_id else "off"
            with st.container(key=f"navitem_{page_id}_{on}"):
                if st.button(
                    label if openr else "\u200b",
                    icon=f":material/{icon}:",
                    key=f"nav_{page_id}",
                    help=label,
                    width="stretch",
                ):
                    set_nav_page(page_id)
                    st.rerun()

    if not openr:
        return

    ok = not validation_errors
    led = "ok" if ok else "deny"
    valid_text = "Topologi valid" if ok else f"Topologi bermasalah ({len(validation_errors)})"
    st.html(
        '<div class="fw-rail-status" translate="no">'
        f'<div title="Nomor yang naik setiap konfigurasi berubah; hasil uji lama ditandai usang.">'
        f"Revisi konfigurasi <b>{state.config_revision}</b></div>"
        f'<div><span class="fw-led {led}"></span>{valid_text}</div>'
        f"<div><b>{len(state.devices)}</b> perangkat, <b>{len(state.rules)}</b> rule</div>"
        "</div>"
    )
