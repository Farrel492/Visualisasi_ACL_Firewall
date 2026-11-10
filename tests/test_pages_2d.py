"""Tes halaman Log Trafik, Pusat Peringatan, dan Lab Belajar (AppTest; jalankan di terminal biasa)."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from firewall_sim.scenarios.presets import default_lab
from firewall_sim.ui import labels
from firewall_sim.ui.state import KEY_EVENTS, KEY_PAIRS, KEY_STATE

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


def test_labels_rule_label_and_friendly_text():
    state = default_lab()
    assert labels.rule_label(state, None) == "kebijakan default"
    assert labels.rule_label(state, "tidak_ada") == "aturan sudah dihapus"
    text = labels.friendly_text(state, "Paket dari pc_a: Cocok dengan rule ID 'x' (order 3)")
    assert "PC A" in text and "aturan #3" in text and "rule ID" not in text


def test_logs_table_uses_names_and_rule_numbers():
    at = _demo_app()
    _goto(at, "traffic_logs")
    flat = " ".join(d.value.to_string() for d in at.dataframe)
    assert "PC B" in flat and "Web Server" in flat and "aturan #2" in flat
    assert "pc_b" not in flat and "demo_rule" not in flat and "log_test" not in flat


def test_logs_filter_by_decision():
    at = _demo_app()
    _goto(at, "traffic_logs")
    at.selectbox(key="sel_log_dec").select("DROP").run()
    assert not at.exception
    frame = at.dataframe[0].value
    assert len(frame) == 1 and list(frame["Keputusan"]) == ["DROP"]


def test_logs_search_accepts_device_name():
    at = _demo_app()
    _goto(at, "traffic_logs")
    at.text_input(key="input_log_search").set_value("PC A").run()
    assert not at.exception
    frame = at.dataframe[0].value
    assert len(frame) == 1 and list(frame["Sumber"]) == ["PC A"]


def test_alerts_keep_policy_notice_and_can_acknowledge():
    at = _demo_app()
    _goto(at, "alerts")
    assert any("BUKAN OTOMATIS" in w.value for w in at.warning)
    assert at.session_state[KEY_EVENTS][0].acknowledged is False
    [b for b in at.button if b.key == "btn_ack_one"][0].click().run()
    assert not at.exception
    assert at.session_state[KEY_EVENTS][0].acknowledged is True
    assert "sudah ditinjau" in " ".join(d.value.to_string() for d in at.dataframe)


def test_lab_load_and_test_reports_pass_and_clears_old_results():
    at = _demo_app()
    assert len(at.session_state[KEY_PAIRS]) == 2
    _goto(at, "learning_lab")
    [b for b in at.button if b.key == "load_scen_web_allow"][0].click().run()
    assert not at.exception
    assert dict(at.session_state[KEY_STATE].scenario_metadata).get("id") == "scen_web_allow"
    assert len(at.session_state[KEY_PAIRS]) == 1, "hasil uji topologi lama harus dibersihkan"
    assert any("Lulus" in s.value for s in at.success)


def test_lab_load_only_runs_no_test():
    at = _demo_app()
    _goto(at, "learning_lab")
    [b for b in at.button if b.key == "load_only_scen_web_allow"][0].click().run()
    assert not at.exception
    assert len(at.session_state[KEY_PAIRS]) == 0
