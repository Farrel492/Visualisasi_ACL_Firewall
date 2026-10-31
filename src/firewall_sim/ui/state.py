"""UI state manager and bridge to core engine and ConfigService.

ATURAN ARSITEKTUR:
- Satu-satunya jembatan antara antarmuka Streamlit dan engine/ConfigService.
- Halaman UI DILARANG memutasi state secara langsung; semua mutasi wajib lewat apply_command.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Tuple
import streamlit as st

from firewall_sim.ui import workspace as ws

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
KEY_ALERT_HIGHLIGHT = "fw_sim_alert_highlight"
KEY_NAV_PAGE = "nav_page"
KEY_TOKEN = "fw_sim_workspace_token"
KEY_LAYOUT = "fw_sim_layout"
KEY_CABLES = "fw_sim_cables"
KEY_RAIL_OPEN = "fw_sim_rail_open"
KEY_LAST_SAVED = "fw_sim_last_saved_hash"
KEY_NOTICE = "fw_sim_notice"
KEY_SELECTED_DEVICE = "fw_sim_selected_device"
KEY_CLI_DEVICE = "fw_sim_cli_device"
KEY_CLI_MODE = "fw_sim_cli_mode"


def _fresh_defaults() -> None:
    st.session_state[KEY_NAV_PAGE] = "start_here"
    st.session_state[KEY_STATE] = default_lab()
    st.session_state[KEY_HISTORY] = []
    st.session_state[KEY_PAIRS] = []
    st.session_state[KEY_TRAFFIC_LOGS] = []
    st.session_state[KEY_EVENTS] = []
    st.session_state[KEY_CLI_LOG] = []
    st.session_state[KEY_ALERT_HIGHLIGHT] = True
    st.session_state[KEY_LAYOUT] = {}
    st.session_state[KEY_CABLES] = {}
    st.session_state[KEY_RAIL_OPEN] = True
    st.session_state[KEY_SELECTED_DEVICE] = None
    st.session_state[KEY_CLI_DEVICE] = None
    st.session_state[KEY_CLI_MODE] = "user"


def _apply_snapshot(snap: Dict[str, Any]) -> None:
    st.session_state[KEY_STATE] = snap["state"]
    st.session_state[KEY_PAIRS] = list(snap["pairs"])
    st.session_state[KEY_HISTORY] = [r for _, r in snap["pairs"]]
    st.session_state[KEY_TRAFFIC_LOGS] = list(snap["logs"])
    st.session_state[KEY_EVENTS] = list(snap["events"])
    st.session_state[KEY_CLI_LOG] = list(snap["cli_log"])
    st.session_state[KEY_MODE] = snap.get("mode", "Learning")
    st.session_state[KEY_LAYOUT] = dict(snap.get("layout", {}))
    st.session_state[KEY_CABLES] = dict(snap.get("cables", {}))


def init_session_state() -> None:
    """Menyiapkan session state. Pada sesi baru, workspace lama dimuat dari token di URL."""
    if KEY_STATE in st.session_state:
        return

    _fresh_defaults()
    token = None
    try:
        token = st.query_params.get("w")
    except Exception:  # noqa: BLE001
        token = None

    restored = False
    if ws.is_valid_token(token):
        snap, errors = ws.read_snapshot(token)
        if snap is not None:
            _apply_snapshot(snap)
            restored = True
            st.session_state[KEY_NOTICE] = "Pekerjaan sebelumnya dipulihkan."
        elif errors:
            st.session_state[KEY_NOTICE] = "Workspace lama rusak, memulai dari awal."
    if not ws.is_valid_token(token):
        token = ws.new_token()
    st.session_state[KEY_TOKEN] = token
    try:
        st.query_params["w"] = token
    except Exception:  # noqa: BLE001
        pass
    if not restored:
        ws.cleanup_old()


def snapshot_now() -> Dict[str, Any]:
    return {
        "state": st.session_state[KEY_STATE],
        "pairs": list(st.session_state[KEY_PAIRS]),
        "logs": list(st.session_state[KEY_TRAFFIC_LOGS]),
        "events": list(st.session_state[KEY_EVENTS]),
        "cli_log": list(st.session_state[KEY_CLI_LOG]),
        "mode": st.session_state[KEY_MODE],
        "layout": dict(st.session_state[KEY_LAYOUT]),
        "cables": dict(st.session_state[KEY_CABLES]),
    }


def persist_workspace() -> None:
    """Simpan workspace bila ada perubahan sejak penyimpanan terakhir. Dipanggil tiap akhir run."""
    init_session_state()
    try:
        snap = snapshot_now()
        # buang kabel/posisi milik objek yang sudah dihapus
        link_ids = {l.id for l in snap["state"].links}
        dev_ids = {d.id for d in snap["state"].devices}
        snap["cables"] = {k: v for k, v in snap["cables"].items() if k in link_ids}
        snap["layout"] = {k: v for k, v in snap["layout"].items() if k in dev_ids}
        text = ws.snapshot_to_json(snap)
        digest = hashlib.sha1(text.encode("utf-8")).hexdigest()
        # saved_at selalu berubah, jadi hash dihitung tanpa field itu
        body = text.split('"saved_at"')[0] + text.split('"project"', 1)[1]
        digest = hashlib.sha1(body.encode("utf-8")).hexdigest()
        if st.session_state.get(KEY_LAST_SAVED) != digest:
            if ws.write_snapshot(st.session_state[KEY_TOKEN], snap):
                st.session_state[KEY_LAST_SAVED] = digest
    except Exception:  # noqa: BLE001
        # Penyimpanan tidak boleh menjatuhkan aplikasi.
        pass


def new_workspace() -> None:
    """Mulai workspace baru dengan token baru (workspace lama tetap tersimpan di berkas)."""
    for key in list(st.session_state.keys()):
        if key.startswith("fw_sim_") or key == KEY_NAV_PAGE:
            del st.session_state[key]
    st.session_state[KEY_NOTICE] = ""
    try:
        st.query_params.clear()
    except Exception:  # noqa: BLE001
        pass


def pop_notice() -> str:
    init_session_state()
    msg = st.session_state.get(KEY_NOTICE, "")
    st.session_state[KEY_NOTICE] = ""
    return msg or ""


# --- layout, kabel, pemilihan perangkat -------------------------------------------------


def get_layout() -> Dict[str, List[float]]:
    init_session_state()
    return dict(st.session_state[KEY_LAYOUT])


def set_layout(positions: Dict[str, List[float]]) -> None:
    init_session_state()
    clean = {}
    for dev_id, xy in positions.items():
        try:
            clean[str(dev_id)] = [round(float(xy[0]), 1), round(float(xy[1]), 1)]
        except (TypeError, ValueError, IndexError):
            continue
    merged = dict(st.session_state[KEY_LAYOUT])
    merged.update(clean)
    st.session_state[KEY_LAYOUT] = merged


def reset_layout() -> None:
    init_session_state()
    st.session_state[KEY_LAYOUT] = {}


def get_cables() -> Dict[str, str]:
    init_session_state()
    return dict(st.session_state[KEY_CABLES])


def set_cable(link_id: str, kind: str) -> None:
    init_session_state()
    cables = dict(st.session_state[KEY_CABLES])
    cables[link_id] = kind
    st.session_state[KEY_CABLES] = cables


def get_selected_device() -> Optional[str]:
    init_session_state()
    return st.session_state.get(KEY_SELECTED_DEVICE)


def set_selected_device(dev_id: Optional[str]) -> None:
    init_session_state()
    st.session_state[KEY_SELECTED_DEVICE] = dev_id


def is_rail_open() -> bool:
    init_session_state()
    return bool(st.session_state.get(KEY_RAIL_OPEN, True))


def toggle_rail() -> None:
    init_session_state()
    st.session_state[KEY_RAIL_OPEN] = not is_rail_open()


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
    st.session_state[KEY_LAYOUT] = {}
    st.session_state[KEY_CABLES] = {}


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


def clear_test_history() -> None:
    """Hapus riwayat uji (hasil + pasangan paket) tanpa menyentuh log dan peringatan."""
    init_session_state()
    st.session_state[KEY_HISTORY] = []
    st.session_state[KEY_PAIRS] = []


def clear_traffic_logs() -> None:
    init_session_state()
    st.session_state[KEY_TRAFFIC_LOGS] = []


def clear_security_events() -> None:
    init_session_state()
    st.session_state[KEY_EVENTS] = []


def clear_cli_history() -> None:
    init_session_state()
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

