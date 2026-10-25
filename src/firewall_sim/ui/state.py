"""UI state manager and bridge to core engine and ConfigService.

ATURAN ARSITEKTUR:
- Satu-satunya jembatan antara antarmuka Streamlit dan engine/ConfigService.
- Halaman UI DILARANG memutasi state secara langsung; semua mutasi wajib lewat apply_command.
- Mode UI ("Learning" vs "Professional") disimpan murni di session_state dan tidak menyentuh ProjectState (T11).
"""

from __future__ import annotations

from typing import List, Optional, Tuple
import streamlit as st

from firewall_sim.config.service import AddRule, ConfigCommand, update_config
from firewall_sim.core.alerts import AlertPolicy, derive_alerts
from firewall_sim.core.analytics import TrafficLogEntry, create_log_entry
from firewall_sim.core.models import (
    Action,
    Chain,
    FirewallRule,
    PacketTest,
    ProjectState,
    Protocol,
    SecurityEvent,
    SimulationResult,
)
from firewall_sim.core.simulator import simulate_packet
from firewall_sim.scenarios.presets import default_lab, empty_project


KEY_STATE = "fw_sim_project_state"
KEY_HISTORY = "fw_sim_history"
KEY_PAIRS = "fw_sim_pairs"
KEY_TRAFFIC_LOGS = "fw_sim_traffic_logs"
KEY_EVENTS = "fw_sim_events"
KEY_CLI_LOG = "fw_sim_cli_log"
KEY_MODE = "fw_sim_ui_mode"
KEY_ALERT_HIGHLIGHT = "fw_sim_alert_highlight"
KEY_NAV_PAGE = "nav_page"


def init_session_state() -> None:
    """Menginisialisasi session state jika belum ada."""
    if KEY_NAV_PAGE not in st.session_state:
        st.session_state[KEY_NAV_PAGE] = "start_here"
    if KEY_STATE not in st.session_state:
        st.session_state[KEY_STATE] = default_lab()
    if KEY_HISTORY not in st.session_state:
        st.session_state[KEY_HISTORY] = []
    if KEY_PAIRS not in st.session_state:
        st.session_state[KEY_PAIRS] = []
    if KEY_TRAFFIC_LOGS not in st.session_state:
        st.session_state[KEY_TRAFFIC_LOGS] = []
    if KEY_EVENTS not in st.session_state:
        st.session_state[KEY_EVENTS] = []
    if KEY_CLI_LOG not in st.session_state:
        st.session_state[KEY_CLI_LOG] = []
    if KEY_MODE not in st.session_state:
        st.session_state[KEY_MODE] = "Learning"
    if KEY_ALERT_HIGHLIGHT not in st.session_state:
        st.session_state[KEY_ALERT_HIGHLIGHT] = True


def get_ui_mode() -> str:
    """Mengambil mode UI saat ini ('Learning' atau 'Professional')."""
    init_session_state()
    return st.session_state[KEY_MODE]


def set_ui_mode(mode: str) -> None:
    """Mengubah mode UI tanpa memutasi ProjectState."""
    init_session_state()
    st.session_state[KEY_MODE] = mode


def get_state() -> ProjectState:
    """Mengambil instance ProjectState aktif."""
    init_session_state()
    return st.session_state[KEY_STATE]


def set_project_state(new_state: ProjectState) -> None:
    """Menyimpan project state baru (misalnya setelah load JSON atau load preset)."""
    init_session_state()
    st.session_state[KEY_STATE] = new_state


def set_state_from_cli(new_state: ProjectState) -> None:
    """Menyimpan state baru yang dihasilkan oleh CLI parser."""
    set_project_state(new_state)


def apply_command(command: ConfigCommand, source: str = "GUI") -> Tuple[bool, List[str]]:
    """Menerapkan mutasi konfigurasi melalui ConfigService satu pintu.

    Returns:
        (success: bool, errors: list[str])
    """
    init_session_state()
    current_state = st.session_state[KEY_STATE]

    # Pastikan source diset sesuai konteks pemanggil
    if hasattr(command, "source"):
        object.__setattr__(command, "source", source)

    new_state, errors = update_config(current_state, command)
    if errors:
        return False, errors

    st.session_state[KEY_STATE] = new_state
    return True, []


def reset_to_preset(preset_name: str) -> None:
    """Mereset project state ke preset tertentu."""
    init_session_state()
    if preset_name == "empty":
        st.session_state[KEY_STATE] = empty_project()
    else:
        st.session_state[KEY_STATE] = default_lab()


def add_simulation_run(packet: PacketTest, result: SimulationResult) -> None:
    """Menyimpan hasil simulasi paket, membuat traffic log entry, dan mengekstrak alert."""
    init_session_state()

    # Simpan pasangan (packet, result)
    pairs: List[Tuple[PacketTest, SimulationResult]] = st.session_state[KEY_PAIRS]
    pairs.insert(0, (packet, result))

    # Simpan hasil simulasi
    history: List[SimulationResult] = st.session_state[KEY_HISTORY]
    history.insert(0, result)

    # Buat traffic log entry
    log_entry = create_log_entry(packet, result)
    logs: List[TrafficLogEntry] = st.session_state[KEY_TRAFFIC_LOGS]
    logs.insert(0, log_entry)

    # Derivasi alert keamanan jika terjadi DROP
    policy = AlertPolicy(highlight_drop=st.session_state.get(KEY_ALERT_HIGHLIGHT, True))
    alerts = derive_alerts(result, policy)
    events: List[SecurityEvent] = st.session_state[KEY_EVENTS]
    for ev in alerts:
        events.insert(0, ev)


def add_simulation_result(result: SimulationResult) -> None:
    """Fallback kompatibilitas untuk hasil simulasi tanpa referensi packet penuh."""
    dummy_pkt = PacketTest(
        id=result.test_id,
        source_device_id="unknown",
        destination_target=None,
    )
    add_simulation_run(dummy_pkt, result)


def get_simulation_pairs() -> List[Tuple[PacketTest, SimulationResult]]:
    """Mengambil pasangan (PacketTest, SimulationResult) yang telah dijalankan."""
    init_session_state()
    return list(st.session_state[KEY_PAIRS])


def get_simulation_history() -> List[SimulationResult]:
    """Mengambil riwayat hasil simulasi paket."""
    init_session_state()
    return list(st.session_state[KEY_HISTORY])


def get_traffic_logs() -> List[TrafficLogEntry]:
    """Mengambil riwayat log trafik jaringan simulasi."""
    init_session_state()
    return list(st.session_state[KEY_TRAFFIC_LOGS])


def get_security_events() -> List[SecurityEvent]:
    """Mengambil riwayat event keamanan."""
    init_session_state()
    return list(st.session_state[KEY_EVENTS])


def record_cli_interaction(command: str, output: str, errors: List[str]) -> None:
    """Mencatat riwayat interaksi sesi CLI."""
    init_session_state()
    log_list = st.session_state[KEY_CLI_LOG]
    log_list.append((command, output, errors))


def get_cli_history() -> List[Tuple[str, str, List[str]]]:
    """Mengambil riwayat interaksi sesi CLI."""
    init_session_state()
    return list(st.session_state[KEY_CLI_LOG])


def get_nav_page() -> str:
    """Mengambil id halaman aktif saat ini."""
    init_session_state()
    return st.session_state.get(KEY_NAV_PAGE, "start_here")


def set_nav_page(page: str) -> None:
    """Mengubah halaman navigasi aktif."""
    init_session_state()
    st.session_state[KEY_NAV_PAGE] = page


def clear_simulation_data() -> None:
    """Membersihkan riwayat pengujian, log trafik, dan event keamanan di session state."""
    init_session_state()
    st.session_state[KEY_HISTORY] = []
    st.session_state[KEY_PAIRS] = []
    st.session_state[KEY_TRAFFIC_LOGS] = []
    st.session_state[KEY_EVENTS] = []
    st.session_state[KEY_CLI_LOG] = []


def load_demo_scenario() -> Tuple[bool, List[str]]:
    """Memuat demo siap pakai:
    1. Reset ke default_lab
    2. Bersihkan history/pairs/traffic logs/events
    3. AddRule via apply_command:
       - rule 1: ACCEPT chain forward src 192.168.1.10/32 -> dst 10.0.0.10/32 tcp/80 (PC A -> Web Server)
       - rule 2: DROP chain forward src 192.168.1.11/32 -> dst 10.0.0.10/32 tcp/80 (PC B -> Web Server)
    4. Jalankan kedua uji via simulate_packet + add_simulation_run.
    """
    reset_to_preset("default")
    clear_simulation_data()

    # Rule 1: ACCEPT PC A -> Web Server port 80
    rule1 = FirewallRule(
        id="demo_rule_accept",
        order=1,
        enabled=True,
        chain=Chain.FORWARD,
        src_cidr="192.168.1.10/32",
        dst_cidr="10.0.0.10/32",
        protocol=Protocol.TCP,
        dst_port="80",
        action=Action.ACCEPT,
        comment="Izinkan akses Web Server dari PC A",
    )
    ok1, errs1 = apply_command(AddRule(rule=rule1))
    if not ok1:
        return False, errs1

    # Rule 2: DROP PC B -> Web Server port 80
    rule2 = FirewallRule(
        id="demo_rule_drop",
        order=2,
        enabled=True,
        chain=Chain.FORWARD,
        src_cidr="192.168.1.11/32",
        dst_cidr="10.0.0.10/32",
        protocol=Protocol.TCP,
        dst_port="80",
        action=Action.DROP,
        comment="Blokir akses Web Server dari PC B",
    )
    ok2, errs2 = apply_command(AddRule(rule=rule2))
    if not ok2:
        return False, errs2

    # Jalankan kedua uji paket
    state = get_state()
    pkt1 = PacketTest(
        id="pkt_demo_pc_a",
        source_device_id="pc_a",
        destination_device_id="server",
        destination_ip="10.0.0.10",
        protocol=Protocol.TCP,
        src_port=49152,
        dst_port=80,
    )
    res1 = simulate_packet(state, pkt1)
    add_simulation_run(pkt1, res1)

    pkt2 = PacketTest(
        id="pkt_demo_pc_b",
        source_device_id="pc_b",
        destination_device_id="server",
        destination_ip="10.0.0.10",
        protocol=Protocol.TCP,
        src_port=49153,
        dst_port=80,
    )
    res2 = simulate_packet(state, pkt2)
    add_simulation_run(pkt2, res2)

    return True, []

