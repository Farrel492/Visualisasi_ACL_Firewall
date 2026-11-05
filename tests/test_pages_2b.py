"""Tes halaman Aturan Firewall dan Konfigurasi Perangkat (AppTest; jalankan di terminal biasa)."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from firewall_sim.ui.pages import firewall_rules as fr
from firewall_sim.scenarios.presets import default_lab
from firewall_sim.ui.state import KEY_NAV_PAGE, KEY_SELECTED_DEVICE, KEY_STATE

APP_PATH = str(Path(__file__).parent.parent / "app.py")


def _demo_app():
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    [b for b in at.button if b.key == "btn_next_action"][0].click().run()
    assert not at.exception
    return at


def _goto(at, page):
    [b for b in at.button if b.key == f"nav_{page}"][0].click().run()
    assert not at.exception, [e.value for e in at.exception]


def test_endpoint_label_uses_device_names():
    state = default_lab()
    assert fr.endpoint_label(state, "192.168.1.10/32") == "PC A (192.168.1.10)"
    assert fr.endpoint_label(state, None) == "semua"
    assert fr.endpoint_label(state, "192.168.1.0/24") == "192.168.1.0/24 (subnet)"


def test_rules_table_has_text_status_and_no_internal_ids():
    at = _demo_app()
    _goto(at, "firewall_rules")
    html = " ".join(m.value for m in at.markdown)
    assert "PC A (192.168.1.10)" in html and "Web Server (10.0.0.10)" in html
    assert "demo_rule" not in html


def test_rules_toggle_marks_rule_nonaktif_in_text():
    at = _demo_app()
    _goto(at, "firewall_rules")
    [b for b in at.button if b.key == "toggle_forward"][0].click().run()
    assert not at.exception
    rules = sorted(at.session_state[KEY_STATE].rules, key=lambda r: r.order)
    assert rules[0].enabled is False
    assert "nonaktif" in " ".join(m.value for m in at.markdown)


def test_rules_move_down_swaps_order():
    at = _demo_app()
    _goto(at, "firewall_rules")
    before = [r.id for r in sorted(at.session_state[KEY_STATE].rules, key=lambda r: r.order)]
    [b for b in at.button if b.key == "down_forward"][0].click().run()
    rules_after = sorted(at.session_state[KEY_STATE].rules, key=lambda r: r.order)
    after = [r.id for r in rules_after]
    assert after == list(reversed(before))
    assert len({r.order for r in rules_after}) == len(rules_after), "nomor urut harus tetap unik"


def test_rules_add_rule_from_device_choice():
    at = _demo_app()
    _goto(at, "firewall_rules")
    at.selectbox(key="sel_rule_dst").select("10.0.0.10/32")
    at.text_input(key="input_rule_dport").set_value("443")
    [b for b in at.button if b.key == "btn_add_rule"][0].click().run()
    assert not at.exception
    rules = at.session_state[KEY_STATE].rules
    assert len(rules) == 3
    assert any(r.dst_cidr == "10.0.0.10/32" and r.dst_port == "443" for r in rules)


def test_device_config_selectbox_changes_selected_device():
    at = _demo_app()
    _goto(at, "device_config")
    at.selectbox(key="sel_config_dev").select("pc_b").run()
    assert not at.exception
    assert at.session_state[KEY_SELECTED_DEVICE] == "pc_b"
    assert any(t.key == "input_gw_pc_b" for t in at.text_input)


def test_device_config_invalid_ip_is_not_saved():
    at = _demo_app()
    _goto(at, "device_config")
    at.selectbox(key="sel_config_dev").select("pc_a").run()
    state = at.session_state[KEY_STATE]
    iface = state.get_device("pc_a").interfaces[0]
    before = iface.ipv4_cidr
    at.text_input(key=f"input_ip_{iface.id}").set_value("bukan-ip")
    [b for b in at.button if b.label == "Simpan IP"][0].click().run()
    assert not at.exception
    assert at.session_state[KEY_STATE].get_device("pc_a").interfaces[0].ipv4_cidr == before
    assert any("tidak valid" in e.value for e in at.error)


def test_network_inspector_selectbox_keeps_user_choice():
    at = _demo_app()
    _goto(at, "network")
    at.selectbox(key="sel_inspect_dev").select("server").run()
    assert not at.exception
    assert at.session_state[KEY_SELECTED_DEVICE] == "server"
    assert at.selectbox(key="sel_inspect_dev").value == "server"


def test_overview_recent_tests_table_uses_device_names():
    at = _demo_app()
    _goto(at, "overview")
    frames = [d.value for d in at.dataframe]
    flat = str(frames)
    assert "PC B" in flat and "Web Server" in flat
    assert "pc_b" not in flat
