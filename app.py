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

import os

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
from firewall_sim.ui.shell import PAGE_LABELS, render_rail
from firewall_sim.ui.theme import inject_theme_css
from firewall_sim.ui.state import (
    KEY_NAV_PAGE,
    get_nav_page,
    get_state,
    init_session_state,
    persist_workspace,
    set_nav_page,
)

st.set_page_config(
    page_title="Firewall Simulator",
    page_icon=":material/shield:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session_state()

ALIAS_MAP = {
    "start": "start_here",
    "rules": "firewall_rules",
    "devices": "device_config",
    "cli": "cli_console",
    "dashboard": "overview",
}

# Tautan langsung ke halaman: ?halaman=network (dipakai juga untuk screenshot).
# ?demo=1 hanya aktif bila FW_DEV=1 (untuk pengembangan, bukan untuk pengguna).
if not st.session_state.get("fw_sim_qp_applied"):
    st.session_state["fw_sim_qp_applied"] = True
    wanted_page = st.query_params.get("halaman")
    if wanted_page:
        wanted_page = ALIAS_MAP.get(wanted_page, wanted_page)
        if wanted_page in PAGE_LABELS:
            set_nav_page(wanted_page)
    if os.environ.get("FW_DEV") == "1" and st.query_params.get("demo") == "1":
        from firewall_sim.ui.state import load_demo_scenario

        load_demo_scenario()

current_nav = ALIAS_MAP.get(get_nav_page(), get_nav_page())
if current_nav != get_nav_page():
    set_nav_page(current_nav)

current_state = get_state()
validation_errors = validate_topology(current_state)

st.markdown(inject_theme_css(), unsafe_allow_html=True)

rail = st.container(key="fw_rail")
main = st.container(key="fw_main")

with rail:
    render_rail(current_state, validation_errors)

PAGES = {
    "start_here": render_start_here_page,
    "overview": render_overview_page,
    "network": render_network_page,
    "viz3d": render_viz3d_page,
    "device_config": render_device_config_page,
    "firewall_rules": render_firewall_rules_page,
    "packet_sim": render_packet_sim_page,
    "traffic_logs": render_traffic_logs_page,
    "alerts": render_alerts_page,
    "learning_lab": render_learning_lab_page,
    "cli_console": render_cli_console_page,
}

active_page = ALIAS_MAP.get(get_nav_page(), get_nav_page())
if active_page not in PAGES:
    active_page = "start_here"

with main:
    with st.container(key=f"fw_page_{active_page}"):
        PAGES[active_page]()

# Simpan otomatis: pekerjaan tetap ada setelah halaman di-refresh (token di URL ?w=...)
persist_workspace()
