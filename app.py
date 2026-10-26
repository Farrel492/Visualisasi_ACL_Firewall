"""Firewall Simulator - Main Application Entry Point.

PENTING:
Seluruh aktivitas dan pengujian pada aplikasi ini adalah SIMULASI semata.
Tidak ada koneksi ke perangkat jaringan nyata atau lalu lintas live.
"""

from pathlib import Path
import sys

# Memastikan direktori src/ dapat diimpor langsung
SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import streamlit as st

from firewall_sim.core.validation import validate_topology
from firewall_sim.ui.pages.alerts import render_alerts_page
from firewall_sim.ui.pages.cli_console import render_cli_console_page
from firewall_sim.ui.pages.device_config import render_device_config_page
from firewall_sim.ui.pages.firewall_rules import render_firewall_rules_page
from firewall_sim.ui.pages.learning_lab import render_learning_lab_page
from firewall_sim.ui.pages.network import render_network_page
from firewall_sim.ui.pages.overview import render_overview_page
from firewall_sim.ui.pages.packet_sim import render_packet_sim_page
from firewall_sim.ui.pages.start_here import render_start_here_page
from firewall_sim.ui.pages.traffic_logs import render_traffic_logs_page
from firewall_sim.ui.pages.viz3d_page import render_viz3d_page
from firewall_sim.ui.state import (
    KEY_NAV_PAGE,
    get_nav_page,
    get_state,
    get_ui_mode,
    init_session_state,
    set_nav_page,
    set_ui_mode,
)

st.set_page_config(
    page_title="Firewall Simulator",
    page_icon=":material/shield:",
    layout="wide",
)

# Integrasi Logo dan Icon untuk Sidebar (mendukung mode terbuka & ciut)
LOGO_PATH = SRC_DIR / "firewall_sim" / "ui" / "assets" / "logo.svg"
ICON_PATH = SRC_DIR / "firewall_sim" / "ui" / "assets" / "icon.svg"
if LOGO_PATH.exists() and ICON_PATH.exists():
    st.logo(str(LOGO_PATH), icon_image=str(ICON_PATH))

# Inisialisasi ProjectState dalam session state
init_session_state()

# Normalisasi nav_page dan alias
ALIAS_MAP = {
    "start": "start_here",
    "rules": "firewall_rules",
    "devices": "device_config",
    "cli": "cli_console",
    "dashboard": "overview",
}
current_nav = get_nav_page()
if current_nav in ALIAS_MAP:
    current_nav = ALIAS_MAP[current_nav]
    set_nav_page(current_nav)

# Status Ringkas Konfigurasi pada Sidebar
current_state = get_state()
validation_errors = validate_topology(current_state)
is_valid = (len(validation_errors) == 0)
curr_mode = get_ui_mode()

with st.sidebar.container(border=True):
    st.markdown("#### :material/info: Status Sistem")
    st.caption(
        f"**Revisi konfigurasi: #{current_state.config_revision}**",
        help="Revisi konfigurasi: nomor atomik yang naik setiap perubahan; hasil uji lama ditandai usang.",
    )
    if is_valid:
        st.caption(
            "**Topologi: valid**",
            help="Topologi: valid / tidak ada konflik subnet, IP duplikat, atau link putus.",
        )
    else:
        st.caption(
            f"**Topologi: ada masalah ({len(validation_errors)} error)**",
            help=f"Topologi: terdeteksi masalah integritas konfigurasi: {validation_errors[0]}",
        )
    mode_label = "Belajar" if curr_mode == "Learning" else "Profesional"
    st.caption(
        f"**Mode: {mode_label}**",
        help="Mode: Belajar (panduan konsep & hint) / Profesional (tata letak padat & teknis).",
    )
    st.caption(
        f":material/devices: {len(current_state.devices)} Perangkat &bull; "
        f":material/security: {len(current_state.rules)} Rule"
    )

# Pilihan Mode Antarmuka (Learning vs Professional)
mode_choice = st.sidebar.radio(
    "Mode Antarmuka:",
    ["Mode Belajar (Learning)", "Mode Profesional"],
    index=0 if curr_mode == "Learning" else 1,
    key="ui_mode_selector",
)
selected_mode_clean = "Learning" if "Learning" in mode_choice else "Professional"
if selected_mode_clean != curr_mode:
    set_ui_mode(selected_mode_clean)
    st.rerun()

# 4 Grup Navigasi Sidebar
NAV_GROUPS = [
    (
        "Mulai",
        [
            ("nav_start_here", "start_here", "Mulai di Sini", ":material/explore:"),
            ("nav_overview", "overview", "Dasbor", ":material/dashboard:"),
        ],
    ),
    (
        "Bangun & Konfigurasi",
        [
            ("nav_network", "network", "Topologi 2D", ":material/hub:"),
            ("nav_device_config", "device_config", "Konfigurasi Perangkat", ":material/settings:"),
            ("nav_firewall_rules", "firewall_rules", "Aturan Firewall", ":material/security:"),
        ],
    ),
    (
        "Simulasi & Visual",
        [
            ("nav_packet_sim", "packet_sim", "Simulasi Paket", ":material/send:"),
            ("nav_viz3d", "viz3d", "Visualisasi 3D", ":material/view_in_ar:"),
        ],
    ),
    (
        "Analisis & Belajar",
        [
            ("nav_traffic_logs", "traffic_logs", "Log Trafik", ":material/list_alt:"),
            ("nav_alerts", "alerts", "Pusat Peringatan", ":material/notifications_active:"),
            ("nav_learning_lab", "learning_lab", "Lab Belajar", ":material/school:"),
            ("nav_cli_console", "cli_console", "Konsol CLI", ":material/terminal:"),
        ],
    ),
]

for group_title, items in NAV_GROUPS:
    st.sidebar.caption(f"**{group_title}**")
    for key, page_id, label, icon in items:
        is_active = (current_nav == page_id)
        btn_type = "primary" if is_active else "secondary"
        if st.sidebar.button(
            f"{icon} {label}",
            key=key,
            type=btn_type,
            use_container_width=True,
        ):
            set_nav_page(page_id)
            st.rerun()

# Router Halaman
active_page = get_nav_page()
if active_page in ALIAS_MAP:
    active_page = ALIAS_MAP[active_page]

if active_page == "start_here":
    render_start_here_page()
elif active_page == "overview":
    render_overview_page()
elif active_page == "network":
    render_network_page()
elif active_page == "viz3d":
    render_viz3d_page()
elif active_page == "device_config":
    render_device_config_page()
elif active_page == "firewall_rules":
    render_firewall_rules_page()
elif active_page == "packet_sim":
    render_packet_sim_page()
elif active_page == "traffic_logs":
    render_traffic_logs_page()
elif active_page == "alerts":
    render_alerts_page()
elif active_page == "learning_lab":
    render_learning_lab_page()
elif active_page == "cli_console":
    render_cli_console_page()
else:
    render_start_here_page()
