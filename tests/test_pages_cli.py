"""Tes halaman Konsol CLI (AppTest; jalankan di terminal biasa)."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from firewall_sim.ui.state import KEY_CLI_LOG, KEY_NAV_PAGE, KEY_PAIRS, KEY_STATE

APP_PATH = str(Path(__file__).parent.parent / "app.py")


def _cli_app():
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    [b for b in at.button if b.key == "btn_next_action"][0].click().run()
    [b for b in at.button if b.key == "nav_cli_console"][0].click().run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _send(at, command):
    at.text_input[0].set_value(command)
    [b for b in at.button if b.label == "Kirim"][0].click().run()
    assert not at.exception, [e.value for e in at.exception]


def _terminal_text(at):
    return " ".join(m.value for m in at.markdown if "fw-terminal-window" in m.value)


def test_cli_starts_in_user_mode_with_router_prompt():
    at = _cli_app()
    assert at.text_input[0].label == "Router-Firewall>"
    assert "Ketik ? untuk bantuan" in _terminal_text(at)


def test_cli_mode_changes_update_prompt():
    at = _cli_app()
    _send(at, "enable")
    assert at.text_input[0].label == "Router-Firewall#"
    _send(at, "configure terminal")
    assert at.text_input[0].label == "Router-Firewall(config)#"
    _send(at, "interface fa0/1")
    assert at.text_input[0].label == "Router-Firewall(config-if)#"


def test_cli_ip_address_changes_state_and_revision():
    at = _cli_app()
    rev = at.session_state[KEY_STATE].config_revision
    for cmd in ("enable", "configure terminal", "interface fa0/1", "ip address 10.0.0.2 255.255.255.0"):
        _send(at, cmd)
    router = at.session_state[KEY_STATE].get_device("router")
    assert [i.ipv4_cidr for i in router.interfaces if i.name == "Fa0/1"] == ["10.0.0.2/24"]
    assert at.session_state[KEY_STATE].config_revision > rev


def test_cli_unknown_command_shows_error_line():
    at = _cli_app()
    _send(at, "xyzzy")
    assert "tidak dikenali" in _terminal_text(at)


def test_cli_ping_from_pc_is_recorded_as_test_result():
    at = _cli_app()
    at.selectbox(key="sel_cli_device").select("pc_b").run()
    assert at.text_input[0].label == "C:\\>"
    before = len(at.session_state[KEY_PAIRS])
    _send(at, "ping 10.0.0.10")
    assert len(at.session_state[KEY_PAIRS]) == before + 1
    # aturan demo hanya memblokir TCP/80, jadi ICMP dari PC B lolos
    assert "Reply from 10.0.0.10" in _terminal_text(at)


def test_cli_log_survives_workspace_roundtrip():
    from firewall_sim.ui import workspace as ws

    at = _cli_app()
    _send(at, "enable")
    snap = {
        "state": at.session_state[KEY_STATE], "pairs": [], "logs": [], "events": [],
        "cli_log": list(at.session_state[KEY_CLI_LOG]), "layout": {}, "cables": {},
    }
    back, errors = ws.snapshot_from_json(ws.snapshot_to_json(snap))
    assert errors == [] and back["cli_log"][0]["c"] == "enable"
