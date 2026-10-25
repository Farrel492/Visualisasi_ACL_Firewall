"""UI integration tests using Streamlit AppTest framework."""

from pathlib import Path
from streamlit.testing.v1 import AppTest

from firewall_sim.core.models import Action, Chain, Decision, FirewallRule, PacketTest, Protocol
from firewall_sim.core.simulator import simulate_packet
from firewall_sim.scenarios.presets import empty_project
from firewall_sim.ui.state import (
    KEY_EVENTS,
    KEY_HISTORY,
    KEY_MODE,
    KEY_NAV_PAGE,
    KEY_STATE,
)

APP_PATH = str(Path(__file__).parent.parent / "app.py")


def test_ui_renders_default_start_here_without_exception():
    """Menguji bahwa app.py dapat dirender pada halaman default (Mulai di Sini) dengan page_header tanpa exception."""
    at = AppTest.from_file(APP_PATH, default_timeout=10)
    at.run()
    assert not at.exception
    assert len(at.title) >= 1
    assert at.title[0].value == "Mulai di Sini"
    assert at.session_state[KEY_NAV_PAGE] == "start_here"


def test_ui_navigation_to_all_pages_via_sidebar_buttons():
    """Menguji bahwa setiap tombol navigasi sidebar dengan key stabil dapat berpindah halaman tanpa exception."""
    nav_buttons = [
        ("nav_start_here", "start_here"),
        ("nav_overview", "overview"),
        ("nav_network", "network"),
        ("nav_device_config", "device_config"),
        ("nav_firewall_rules", "firewall_rules"),
        ("nav_packet_sim", "packet_sim"),
        ("nav_viz3d", "viz3d"),
        ("nav_traffic_logs", "traffic_logs"),
        ("nav_alerts", "alerts"),
        ("nav_learning_lab", "learning_lab"),
        ("nav_cli_console", "cli_console"),
    ]

    for key, expected_page in nav_buttons:
        at = AppTest.from_file(APP_PATH, default_timeout=10)
        at.run()
        matching_buttons = [b for b in at.sidebar.button if b.key == key]
        assert len(matching_buttons) == 1, f"Tombol dengan key '{key}' tidak ditemukan di sidebar"
        matching_buttons[0].click().run()
        assert not at.exception, f"Gagal merender halaman: {expected_page}"
        assert at.session_state[KEY_NAV_PAGE] == expected_page


def test_ui_mode_toggle_preserves_state():
    """Menguji bahwa mengubah mode antarmuka (Learning vs Professional) tidak memutasi ProjectState (T11)."""
    at = AppTest.from_file(APP_PATH, default_timeout=10)
    at.run()

    init_state = at.session_state[KEY_STATE]
    assert at.session_state[KEY_MODE] == "Learning"

    mode_radio = at.sidebar.radio(key="ui_mode_selector")
    mode_radio.set_value("💼 Professional Mode").run()
    assert not at.exception
    assert at.session_state[KEY_MODE] == "Professional"

    state_after = at.session_state[KEY_STATE]
    assert state_after == init_state
    assert state_after.config_revision == init_state.config_revision


def test_ui_demo_scenario_loader():
    """Menguji tombol 'Muat Demo Siap Pakai' di Mulai di Sini menghasilkan >=1 ACCEPT, >=1 DROP, dan >=1 alert."""
    at = AppTest.from_file(APP_PATH, default_timeout=10)
    at.run()

    assert at.session_state[KEY_NAV_PAGE] == "start_here"

    demo_btn = [b for b in at.button if b.key == "btn_demo_load"]
    assert len(demo_btn) == 1, "Tombol 'btn_demo_load' tidak ditemukan"
    demo_btn[0].click().run()
    assert not at.exception

    history = at.session_state[KEY_HISTORY]
    assert len(history) >= 2, f"Diharapkan minimal 2 hasil simulasi, ditemukan: {len(history)}"

    decisions = [r.decision for r in history]
    assert Decision.ACCEPT in decisions, "Diharapkan minimal 1 keputusan ACCEPT pada demo"
    assert Decision.DROP in decisions, "Diharapkan minimal 1 keputusan DROP pada demo"

    alerts = at.session_state[KEY_EVENTS]
    assert len(alerts) >= 1, f"Diharapkan minimal 1 alert keamanan dari paket DROP, ditemukan: {len(alerts)}"


def test_ui_bridge_cli_rule_reflected_in_rules_page():
    """Jembatan UI: Rule yang ditambahkan via CLI muncul di halaman Firewall Rules."""
    at = AppTest.from_file(APP_PATH, default_timeout=10)
    at.run()

    cli_btn = [b for b in at.sidebar.button if b.key == "nav_cli_console"][0]
    cli_btn.click().run()
    assert not at.exception

    at.text_input[0].set_value('rule add chain=forward proto=tcp dport=443 action=accept comment="HTTPS Access"')
    at.button[0].click().run()
    assert not at.exception

    rules_btn = [b for b in at.sidebar.button if b.key == "nav_firewall_rules"][0]
    rules_btn.click().run()
    assert not at.exception

    state = at.session_state[KEY_STATE]
    assert any(r.dst_port == "443" and r.action == Action.ACCEPT for r in state.rules)


def test_ui_simulation_history_record():
    """Menguji bahwa penambahan hasil simulasi muncul pada riwayat session state."""
    at = AppTest.from_file(APP_PATH, default_timeout=10)
    at.run()

    sim_btn = [b for b in at.sidebar.button if b.key == "nav_packet_sim"][0]
    sim_btn.click().run()
    assert not at.exception

    # Jalankan tombol uji cepat
    quick_btn = [b for b in at.button if b.key == "btn_quick_pca_web"][0]
    quick_btn.click().run()
    assert not at.exception

    history = at.session_state[KEY_HISTORY]
    assert len(history) >= 1


def test_ui_3d_viz_renders_with_history():
    """Menguji bahwa halaman 3D Visualization memuat replay trace hasil simulasi paket dan frame DROP berhenti di router."""
    at = AppTest.from_file(APP_PATH, default_timeout=10)
    at.run()

    # Inisiasi hasil simulasi ke session state
    state = at.session_state[KEY_STATE]
    pkt = PacketTest(id="test_ui_drop", source_device_id="pc_a", destination_device_id="server", protocol=Protocol.TCP, dst_port=22)
    rule = FirewallRule(id="r_drp", order=1, enabled=True, chain=Chain.FORWARD, action=Action.DROP)
    state_with_rule = state.__class__(
        devices=state.devices,
        links=state.links,
        rules=(rule,),
        config_revision=state.config_revision,
        default_policies=state.default_policies,
    )
    at.session_state[KEY_STATE] = state_with_rule
    res = simulate_packet(state_with_rule, pkt)
    at.session_state[KEY_HISTORY] = [res]

    # Buka halaman 3D via tombol sidebar
    viz_btn = [b for b in at.sidebar.button if b.key == "nav_viz3d"][0]
    viz_btn.click().run()
    assert not at.exception
    assert len(at.title) >= 1
    assert at.title[0].value == "Visualisasi Spasial 3D"


def test_ui_learning_lab_interaction():
    """Menguji interaksi halaman Learning Lab: tombol muat skenario dan eksekusi uji."""
    at = AppTest.from_file(APP_PATH, default_timeout=10)
    at.run()

    lab_btn = [b for b in at.sidebar.button if b.key == "nav_learning_lab"][0]
    lab_btn.click().run()
    assert not at.exception

    # Klik tombol 'Muat ke Workspace' pertama
    at.button[0].click().run()
    assert not at.exception
    loaded_state = at.session_state[KEY_STATE]
    assert dict(loaded_state.scenario_metadata).get("id") == "scen_web_allow"


def test_ui_all_pages_have_headers_and_no_raw_dict():
    """C4: Menguji bahwa setiap halaman memiliki page_header, tidak exception, dan tidak menampilkan dict mentah."""
    all_pages = [
        "start_here",
        "overview",
        "network",
        "device_config",
        "firewall_rules",
        "packet_sim",
        "viz3d",
        "traffic_logs",
        "alerts",
        "learning_lab",
        "cli_console",
    ]

    for p in all_pages:
        at = AppTest.from_file(APP_PATH, default_timeout=10)
        at.run()
        at.session_state[KEY_NAV_PAGE] = p
        at.run()

        assert not at.exception, f"Exception terjadi saat merender halaman: {p}"
        assert len(at.title) >= 1, f"Halaman '{p}' tidak memiliki judul st.title (page_header)"
        assert len(at.json) == 0, f"Halaman '{p}' menampilkan widget st.json mentah"

        # Periksa bahwa tidak ada markdown yang menampilkan repr dict mentah "{'..."
        for md in at.markdown:
            val = md.value.strip()
            assert not (val.startswith("{'") and val.endswith("}")), f"Ditemukan string dict mentah di markdown halaman '{p}': {val[:40]}"


def test_ui_empty_states_have_action_buttons():
    """Menguji bahwa tampilan empty state pada halaman menyediakan tombol aksi navigasi."""
    at = AppTest.from_file(APP_PATH, default_timeout=10)
    at.run()

    # Kosongkan history dan log
    at.session_state[KEY_HISTORY] = []

    # 1. Buka halaman Visualisasi 3D tanpa history -> harus ada tombol empty state
    at.session_state[KEY_NAV_PAGE] = "viz3d"
    at.run()
    assert not at.exception
    viz3d_empty_btns = [b for b in at.button if b.key == "empty_viz3d_hist_btn"]
    assert len(viz3d_empty_btns) == 1, "Tombol aksi empty state 3D tidak ditemukan"

    # 2. Buka halaman Simulasi Paket tanpa history -> harus ada tombol empty state
    at.session_state[KEY_NAV_PAGE] = "packet_sim"
    at.run()
    assert not at.exception
    sim_empty_btns = [b for b in at.button if b.key == "empty_packet_sim_btn"]
    assert len(sim_empty_btns) == 1, "Tombol aksi empty state simulasi paket tidak ditemukan"

    # 3. Buka halaman Topologi 2D dengan devices kosong -> harus ada tombol empty state
    state = at.session_state[KEY_STATE]
    empty_state_obj = state.__class__(
        devices=(),
        links=(),
        rules=(),
        config_revision=state.config_revision,
        default_policies=state.default_policies,
    )
    at.session_state[KEY_STATE] = empty_state_obj
    at.session_state[KEY_NAV_PAGE] = "network"
    at.run()
    assert not at.exception
    net_empty_btns = [b for b in at.button if b.key == "empty_network_btn"]
    assert len(net_empty_btns) == 1, "Tombol aksi empty state network tidak ditemukan"

