"""Acceptance tests mapping 1:1 to PRD Section 12 criteria (T01 - T14)."""

from __future__ import annotations

from datetime import datetime
import pytest

from firewall_sim.config.cli_parser import parse_and_execute
from firewall_sim.config.service import (
    AddRule,
    MoveRule,
    SetGateway,
    SetInterfaceIP,
    ToggleRule,
    update_config,
)
from firewall_sim.core.alerts import AlertPolicy, derive_alerts
from firewall_sim.core.analytics import create_log_entry
from firewall_sim.core.models import (
    Action,
    Chain,
    Decision,
    FirewallRule,
    PacketTest,
    Protocol,
)
from firewall_sim.core.simulator import simulate_packet
from firewall_sim.scenarios.presets import default_lab
from firewall_sim.ui.viz3d import build_replay_frames, calculate_3d_positions


def test_T01_packet_accept_matched_rule():
    """T01: PC A -> Server cocok rule ACCEPT -> Decision ACCEPT, rule tercatat."""
    state = default_lab()
    rule_web = FirewallRule(
        id="r_allow_http",
        order=1,
        enabled=True,
        chain=Chain.FORWARD,
        src_cidr="192.168.1.10/32",
        dst_cidr="10.0.0.10/32",
        protocol=Protocol.TCP,
        dst_port="80",
        action=Action.ACCEPT,
        comment="Allow Web HTTP",
    )
    state, errs = update_config(state, AddRule(rule=rule_web))
    assert not errs

    pkt = PacketTest(
        id="pkt_t01",
        source_device_id="pc_a",
        destination_device_id="server",
        destination_ip="10.0.0.10",
        protocol=Protocol.TCP,
        src_port=49152,
        dst_port=80,
    )
    result = simulate_packet(state, pkt)

    assert result.decision == Decision.ACCEPT
    assert result.matched_rule_id == "r_allow_http"
    assert "ACCEPT" in result.reason


def test_T02_packet_drop_generates_alert_and_log():
    """T02: PC B -> Server cocok DROP -> Decision DROP, event alert & log muncul."""
    state = default_lab()
    rule_drop = FirewallRule(
        id="r_drop_http",
        order=1,
        enabled=True,
        chain=Chain.FORWARD,
        src_cidr="192.168.1.11/32",
        dst_cidr="10.0.0.10/32",
        protocol=Protocol.TCP,
        dst_port="80",
        action=Action.DROP,
        comment="Block PC B HTTP",
    )
    state, errs = update_config(state, AddRule(rule=rule_drop))
    assert not errs

    pkt = PacketTest(
        id="pkt_t02",
        source_device_id="pc_b",
        destination_device_id="server",
        destination_ip="10.0.0.10",
        protocol=Protocol.TCP,
        src_port=49153,
        dst_port=80,
    )
    result = simulate_packet(state, pkt)

    assert result.decision == Decision.DROP
    assert result.matched_rule_id == "r_drop_http"

    # Verifikasi pembuatan log entry
    log_entry = create_log_entry(pkt, result)
    assert log_entry.decision == Decision.DROP
    assert log_entry.source_device == "pc_b"

    # Verifikasi pembuatan event alert
    policy = AlertPolicy(highlight_drop=True)
    alerts = derive_alerts(result, policy)
    assert len(alerts) >= 1
    assert alerts[0].rule_id == "r_drop_http"
    assert alerts[0].severity == "warning"


def test_T03_first_matching_terminal_action_wins():
    """T03: Dua rule cocok berurutan -> Rule pertama aktif menentukan hasil (first-match wins)."""
    state = default_lab()
    # Rule 1 (order 1): DROP port 443
    r1 = FirewallRule(
        id="r_first_drop",
        order=1,
        enabled=True,
        chain=Chain.FORWARD,
        protocol=Protocol.TCP,
        dst_port="443",
        action=Action.DROP,
    )
    # Rule 2 (order 2): ACCEPT port 443
    r2 = FirewallRule(
        id="r_second_accept",
        order=2,
        enabled=True,
        chain=Chain.FORWARD,
        protocol=Protocol.TCP,
        dst_port="443",
        action=Action.ACCEPT,
    )
    state, _ = update_config(state, AddRule(rule=r1))
    state, _ = update_config(state, AddRule(rule=r2))

    pkt = PacketTest(
        id="pkt_t03",
        source_device_id="pc_a",
        destination_device_id="server",
        destination_ip="10.0.0.10",
        protocol=Protocol.TCP,
        dst_port=443,
    )
    result = simulate_packet(state, pkt)

    assert result.decision == Decision.DROP
    assert result.matched_rule_id == "r_first_drop"


def test_T04_disabled_rule_is_ignored():
    """T04: Rule disabled -> Rule diabaikan dalam evaluasi firewall."""
    state = default_lab()
    # Rule disabled yang me-DROP port 80
    r_disabled = FirewallRule(
        id="r_dis",
        order=1,
        enabled=False,
        chain=Chain.FORWARD,
        protocol=Protocol.TCP,
        dst_port="80",
        action=Action.DROP,
    )
    state, _ = update_config(state, AddRule(rule=r_disabled))

    pkt = PacketTest(
        id="pkt_t04",
        source_device_id="pc_a",
        destination_device_id="server",
        destination_ip="10.0.0.10",
        protocol=Protocol.TCP,
        dst_port=80,
    )
    result = simulate_packet(state, pkt)

    # Karena rule order 1 disabled, evaluasi lolos ke default policy (ACCEPT)
    assert result.decision == Decision.ACCEPT
    assert result.matched_rule_id is None
    assert "default policy" in result.reason.lower()


def test_T05_device_ip_change_applied_to_subsequent_tests():
    """T05: IP perangkat diubah -> Pengujian berikutnya memakai IP terbaru dan config_revision naik."""
    state = default_lab()
    rev_init = state.config_revision

    # Ubah IP pc_a dari 192.168.1.10/24 ke 192.168.1.50/24
    state, errs = update_config(
        state,
        SetInterfaceIP(device_id="pc_a", interface_id="if_pc_a", ipv4_cidr="192.168.1.50/24"),
    )
    assert not errs
    assert state.config_revision == rev_init + 1

    pc_a = state.get_device("pc_a")
    assert pc_a.interfaces[0].ipv4_cidr == "192.168.1.50/24"

    # Rule hanya menerima dari 192.168.1.50/32
    r_match_new_ip = FirewallRule(
        id="r_new_ip",
        order=1,
        enabled=True,
        chain=Chain.FORWARD,
        src_cidr="192.168.1.50/32",
        action=Action.ACCEPT,
    )
    state, _ = update_config(state, AddRule(rule=r_match_new_ip))

    pkt = PacketTest(
        id="pkt_t05",
        source_device_id="pc_a",
        destination_device_id="server",
        destination_ip="10.0.0.10",
        protocol=Protocol.TCP,
        dst_port=80,
    )
    result = simulate_packet(state, pkt)
    assert result.decision == Decision.ACCEPT
    assert result.matched_rule_id == "r_new_ip"


def test_T06_cli_added_rule_reflected_in_state():
    """T06: CLI menambah rule -> State konfigurasi mencatat rule yang sama."""
    state = default_lab()
    cmd = 'rule add chain=forward proto=tcp dport=8080 action=drop comment="Block Proxy"'
    new_state, out_text, errors = parse_and_execute(state, cmd)

    assert not errors
    assert any(
        r.dst_port == "8080" and r.action == Action.DROP and r.chain == Chain.FORWARD
        for r in new_state.rules
    )
    assert new_state.config_revision > state.config_revision


def test_T07_gui_modified_rule_reflected_in_cli_show():
    """T07: GUI/Service mengubah rule -> CLI 'show rules' menampilkan nilai terbaru."""
    state = default_lab()
    r = FirewallRule(
        id="rule_dns",
        order=1,
        enabled=True,
        chain=Chain.FORWARD,
        protocol=Protocol.UDP,
        dst_port="53",
        action=Action.ACCEPT,
        comment="DNS Allow",
    )
    state, _ = update_config(state, AddRule(rule=r))

    # Eksekusi CLI show rules
    _, out_text, errors = parse_and_execute(state, "show rules")
    assert not errors
    assert "rule_dns" in out_text
    assert "UDP" in out_text
    assert "ACCEPT" in out_text


def test_T08_unroutable_packet_returns_no_route():
    """T08: Paket tidak memiliki jalur / link putus -> Hasil NO_ROUTE, BUKAN DROP palsu."""
    state = default_lab()

    # Ubah default gateway PC A ke IP yang tidak terhubung
    state, _ = update_config(state, SetGateway(device_id="pc_a", default_gateway="192.168.1.99"))

    pkt = PacketTest(
        id="pkt_t08",
        source_device_id="pc_a",
        destination_device_id="server",
        destination_ip="10.0.0.10",
        protocol=Protocol.TCP,
        dst_port=80,
    )
    result = simulate_packet(state, pkt)

    assert result.decision == Decision.NO_ROUTE
    assert result.decision != Decision.DROP


def test_T09_invalid_ip_prefix_rejected_state_preserved():
    """T09: IP/prefix tidak valid -> Pesan error jelas, state tidak rusak."""
    state = default_lab()
    rev_init = state.config_revision

    # Kirim IP tidak valid
    new_state, errors = update_config(
        state,
        SetInterfaceIP(device_id="pc_a", interface_id="if_pc_a", ipv4_cidr="999.999.1.1/24"),
    )

    assert len(errors) >= 1
    # State tidak berubah sama sekali
    assert new_state.config_revision == rev_init
    assert new_state == state


def test_T10_drop_packet_stops_at_firewall_in_3d_replay():
    """T10: DROP pada firewall -> Replay 3D berhenti di router dan tidak sampai ke tujuan."""
    state = default_lab()
    r_drop = FirewallRule(
        id="r_drop_ssh",
        order=1,
        enabled=True,
        chain=Chain.FORWARD,
        protocol=Protocol.TCP,
        dst_port="22",
        action=Action.DROP,
    )
    state, _ = update_config(state, AddRule(rule=r_drop))

    pkt = PacketTest(
        id="pkt_t10",
        source_device_id="pc_a",
        destination_device_id="server",
        destination_ip="10.0.0.10",
        protocol=Protocol.TCP,
        dst_port=22,
    )
    result = simulate_packet(state, pkt)
    assert result.decision == Decision.DROP

    positions = calculate_3d_positions(state)
    frames = build_replay_frames(result, positions)

    # Frame terakhir harus berada di router
    assert len(frames) >= 1
    last_frame = frames[-1]
    assert last_frame.device_id == "router"
    # Tidak pernah mencapai server
    visited_devices = [f.device_id for f in frames]
    assert "server" not in visited_devices


def test_T11_page_navigation_does_not_mutate_project_state():
    """T11: Navigasi halaman tidak memutasi ProjectState (mutasi hanya sah lewat apply_command)."""
    from firewall_sim.ui.state import get_nav_page, get_state, set_nav_page
    import streamlit as st

    state_before = default_lab()
    st.session_state["fw_sim_project_state"] = state_before
    st.session_state["nav_page"] = "start_here"

    for page in ["network", "device_config", "firewall_rules", "packet_sim", "viz3d", "overview"]:
        set_nav_page(page)
        assert get_nav_page() == page
        state_current = get_state()
        assert state_current == state_before
        assert state_current.config_revision == state_before.config_revision


def test_T12_normal_drop_event_is_not_labeled_attack():
    """T12: Event DROP normal tidak otomatis diberi label serangan/attack."""
    state = default_lab()
    r_drop = FirewallRule(
        id="r_pol_drop",
        order=1,
        enabled=True,
        chain=Chain.FORWARD,
        action=Action.DROP,
    )
    state, _ = update_config(state, AddRule(rule=r_drop))

    pkt = PacketTest(
        id="pkt_t12",
        source_device_id="pc_a",
        destination_device_id="server",
        destination_ip="10.0.0.10",
        protocol=Protocol.TCP,
        dst_port=80,
    )
    result = simulate_packet(state, pkt)
    alerts = derive_alerts(result, AlertPolicy(highlight_drop=True))

    assert len(alerts) >= 1
    for ev in alerts:
        # Tidak ada kata 'serangan' atau 'attack' pada pesan atau tipe
        assert "attack" not in ev.message.lower()
        assert "serangan" not in ev.message.lower()
        assert "attack" not in ev.event_type.lower()
        assert ev.event_type == "FIREWALL_DROP"


def test_T13_historical_results_preserve_config_revision():
    """T13: Riwayat hasil simulasi lama tetap menyimpan config_revision saat simulasi dibuat."""
    state = default_lab()
    pkt = PacketTest(
        id="pkt_t13",
        source_device_id="pc_a",
        destination_device_id="server",
        destination_ip="10.0.0.10",
        protocol=Protocol.TCP,
        dst_port=80,
    )
    res_rev1 = simulate_packet(state, pkt)
    assert res_rev1.config_revision == state.config_revision

    # Naikkan revisi konfigurasi
    state, _ = update_config(
        state,
        SetInterfaceIP(device_id="pc_b", interface_id="if_pc_b", ipv4_cidr="192.168.1.77/24"),
    )
    assert state.config_revision > res_rev1.config_revision

    # Hasil lama tetap memiliki revisi lamanya
    assert res_rev1.config_revision < state.config_revision


def test_T14_unknown_cli_command_safe_error_no_subprocess():
    """T14: Perintah CLI tidak dikenal atau berbahaya menghasilkan error aman tanpa shell execution."""
    state = default_lab()

    # Uji perintah berbahaya
    dangerous_inputs = [
        "rm -rf /",
        "cat /etc/passwd",
        "python -c 'import os; os.system(\"dir\")'",
        "cmd.exe /c calc",
        "perintah_ngawur_12345",
    ]

    for line in dangerous_inputs:
        new_state, out_text, errors = parse_and_execute(state, line)
        assert len(errors) >= 1
        assert new_state == state
        assert any("tidak dikenal" in err.lower() or "sintaks" in err.lower() for err in errors)


def test_B1_learning_lab_scenario_load():
    """B1: Pemuatan skenario Lab Belajar memutasi state dan mengubah nav_page ke network."""
    from firewall_sim.scenarios.presets import list_scenarios
    from firewall_sim.ui.state import get_nav_page, get_state, set_nav_page, set_project_state

    scenarios = list_scenarios()
    assert len(scenarios) >= 4
    sc = scenarios[0]

    new_state = sc.factory()
    set_project_state(new_state)
    set_nav_page("network")

    assert get_state() == new_state
    assert get_nav_page() == "network"


def test_B3_clear_state_functions_isolation():
    """B3: Fungsi clear_* di state.py mengosongkan kategori masing-masing secara terisolasi."""
    from firewall_sim.ui.state import (
        clear_cli_history,
        clear_security_events,
        clear_test_history,
        clear_traffic_logs,
        get_cli_history,
        get_security_events,
        get_simulation_history,
        get_simulation_pairs,
        get_traffic_logs,
        load_demo_scenario,
        record_cli_interaction,
    )

    ok, _ = load_demo_scenario()
    assert ok
    record_cli_interaction("help", "Panduan CLI", [])

    assert len(get_simulation_history()) >= 1
    assert len(get_simulation_pairs()) >= 1
    assert len(get_traffic_logs()) >= 1
    assert len(get_security_events()) >= 1
    assert len(get_cli_history()) >= 1

    clear_test_history()
    assert len(get_simulation_history()) == 0
    assert len(get_simulation_pairs()) == 0
    assert len(get_traffic_logs()) >= 1
    assert len(get_security_events()) >= 1

    clear_traffic_logs()
    assert len(get_traffic_logs()) == 0
    assert len(get_security_events()) >= 1

    clear_security_events()
    assert len(get_security_events()) == 0

    clear_cli_history()
    assert len(get_cli_history()) == 0


def test_B5_workspace_new_and_project_export_import():
    """B5: Proyek baru via new_workspace dan ekspor-impor proyek JSON."""
    from firewall_sim.storage.json_store import load_project, save_project
    from firewall_sim.ui.state import get_state, init_session_state, new_workspace

    init_session_state()
    state = get_state()

    json_text = save_project(state)
    assert "schema_version" in json_text
    assert "devices" in json_text

    imported_state, errors = load_project(json_text)
    assert not errors
    assert imported_state == state

    new_workspace()
    init_session_state()
    assert get_state().config_revision >= 1


# ── Fase 2a: tes unit _compute_strip_data dan helper overview ────────────────

def test_2a_compute_strip_data_default_lab():
    """2a: _compute_strip_data menghitung perangkat, rule, link, dan status validasi dengan benar."""
    from firewall_sim.ui.pages.overview import _compute_strip_data
    from firewall_sim.scenarios.presets import default_lab

    state = default_lab()
    strip = _compute_strip_data(state)

    assert strip["revision"] == state.config_revision
    assert strip["devices"] == len(state.devices)
    assert strip["rules"] == len(state.rules)
    assert strip["links"] == len(state.links)
    assert isinstance(strip["valid"], bool)
    assert isinstance(strip["val_count"], int)


def test_2a_compute_strip_data_valid_true_for_default_lab():
    """2a: default_lab() lulus validasi sehingga valid == True dan val_count == 0."""
    from firewall_sim.ui.pages.overview import _compute_strip_data
    from firewall_sim.scenarios.presets import default_lab

    state = default_lab()
    strip = _compute_strip_data(state)

    assert strip["valid"] is True
    assert strip["val_count"] == 0


def test_2a_decision_color_returns_correct_colors():
    """2a: _decision_color mengembalikan warna berbeda untuk ACCEPT vs DROP."""
    from firewall_sim.ui.pages.overview import _decision_color
    from firewall_sim.core.models import Decision

    accept_color = _decision_color(Decision.ACCEPT)
    drop_color = _decision_color(Decision.DROP)
    no_route_color = _decision_color(Decision.NO_ROUTE)

    assert accept_color != drop_color
    assert no_route_color != accept_color


def test_2a_decision_label_mapping_complete():
    """2a: _DECISION_LABEL mencakup semua 5 nilai Decision."""
    from firewall_sim.ui.pages.overview import _DECISION_LABEL
    from firewall_sim.core.models import Decision

    for decision in Decision:
        assert decision in _DECISION_LABEL, f"Decision {decision} tidak ada di _DECISION_LABEL"


def test_2a_overview_module_importable():
    """2a: overview.py dapat diimpor tanpa error Streamlit runtime."""
    import importlib
    import sys
    # Pastikan modul tidak cached dari import sebelumnya dengan patch
    mod_name = "firewall_sim.ui.pages.overview"
    if mod_name in sys.modules:
        del sys.modules[mod_name]
    # Import harus berhasil; fungsi render memerlukan Streamlit runtime tapi
    # _compute_strip_data dan helper tidak.
    mod = importlib.import_module(mod_name)
    assert hasattr(mod, "render_overview_page")
    assert hasattr(mod, "_compute_strip_data")
    assert hasattr(mod, "_decision_color")
    assert hasattr(mod, "_DECISION_LABEL")
