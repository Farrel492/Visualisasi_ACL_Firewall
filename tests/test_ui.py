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
    mode_radio.set_value("Mode Profesional").run()
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
    assert at.title[0].value == "Visualisasi 3D"


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
    """R1.1 & R1.10: Menguji bahwa setiap halaman memiliki page_header dengan judul sama dengan label navigasi, bebas dict mentah, bebas enum mentah, dan bebas emoji."""
    import re
    emoji_pattern = re.compile(r"[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]|[\u203c\u2049\u2139\u2194-\u21aa]")

    nav_labels = {
        "start_here": "Mulai di Sini",
        "overview": "Dasbor",
        "network": "Topologi 2D",
        "device_config": "Konfigurasi Perangkat",
        "firewall_rules": "Aturan Firewall",
        "packet_sim": "Simulasi Paket",
        "viz3d": "Visualisasi 3D",
        "traffic_logs": "Log Trafik",
        "alerts": "Pusat Peringatan",
        "learning_lab": "Lab Belajar",
        "cli_console": "Konsol CLI",
    }

    for p, expected_title in nav_labels.items():
        at = AppTest.from_file(APP_PATH, default_timeout=10)
        at.run()
        at.session_state[KEY_NAV_PAGE] = p
        at.run()

        assert not at.exception, f"Exception terjadi saat merender halaman: {p}"
        assert len(at.title) >= 1, f"Halaman '{p}' tidak memiliki judul st.title (page_header)"
        assert at.title[0].value == expected_title, f"Judul halaman '{p}' ({at.title[0].value}) tidak sama dengan label navigasi ({expected_title})"
        assert len(at.json) == 0, f"Halaman '{p}' menampilkan widget st.json mentah"

        # Periksa tidak ada string dict mentah, enum mentah, atau emoji
        for md in at.markdown:
            val = md.value.strip()
            assert not (val.startswith("{'") and val.endswith("}")), f"Ditemukan string dict mentah di markdown '{p}': {val[:40]}"
            for raw_enum in ["DeviceType.", "Action.", "Chain.", "Protocol."]:
                assert raw_enum not in val, f"Ditemukan enum mentah '{raw_enum}' pada markdown halaman '{p}': {val[:60]}"
            emojis_found = emoji_pattern.findall(val)
            assert not emojis_found, f"Ditemukan emoji {emojis_found} pada markdown halaman '{p}'"


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


def test_ui_topology_crud_actions():
    """R1.8: Menguji 4 aksi CRUD topologi (tambah perangkat, hubungkan link, putus link, hapus perangkat)."""
    from firewall_sim.core.models import DeviceType, Interface
    from firewall_sim.config.service import AddDevice, AddLink, RemoveDevice, RemoveLink, update_config

    at = AppTest.from_file(APP_PATH, default_timeout=10)
    at.run()

    # 1. Tambah perangkat Switch baru untuk port bebas tambahan
    state = at.session_state[KEY_STATE]
    state, errs_sw = update_config(state, AddDevice(name="Switch 2", type=DeviceType.SWITCH))
    assert not errs_sw, f"Gagal menambah Switch: {errs_sw}"
    at.session_state[KEY_STATE] = state

    # 2. Tambah PC C dengan IP dan gateway valid
    iface_c = Interface(id="if_pc_c", device_id="pc_c", name="eth0", ipv4_cidr="192.168.1.35/24", enabled=True)
    state, errs_pc = update_config(
        state,
        AddDevice(name="PC C", type=DeviceType.PC, device_id="pc_c", interfaces=(iface_c,), default_gateway="192.168.1.1")
    )
    assert not errs_pc, f"Gagal menambah PC: {errs_pc}"
    at.session_state[KEY_STATE] = state

    # 3. Hubungkan link antara PC C dan Switch 2
    state, errs_link = update_config(state, AddLink(interface_a="if_pc_c", interface_b="if_switch_2_p1"))
    assert not errs_link, f"Gagal menghubungkan link: {errs_link}"
    at.session_state[KEY_STATE] = state

    # 4. Putus link
    created_link_id = [l.id for l in at.session_state[KEY_STATE].links if l.interface_a == "if_pc_c"][0]
    state, errs_del_link = update_config(state, RemoveLink(link_id=created_link_id))
    assert not errs_del_link, f"Gagal menghapus link: {errs_del_link}"
    at.session_state[KEY_STATE] = state

    # 5. Hapus perangkat PC C
    state, errs_del_dev = update_config(state, RemoveDevice(device_id="pc_c"))
    assert not errs_del_dev, f"Gagal menghapus perangkat: {errs_del_dev}"
    at.session_state[KEY_STATE] = state


def test_ui_learning_vs_professional_mode_elements():
    """R1.7: Menguji bahwa elemen edukasi ditampilkan pada Learning Mode dan disembunyikan pada Professional Mode."""
    # 1. Learning Mode
    at_learn = AppTest.from_file(APP_PATH, default_timeout=10)
    at_learn.run()
    at_learn.session_state[KEY_NAV_PAGE] = "firewall_rules"
    at_learn.run()
    assert not at_learn.exception
    # Harus ada panel 'Konsep Penting'
    learn_mds = [m.value for m in at_learn.markdown if "Konsep Penting" in m.value]
    assert len(learn_mds) >= 1, "Panel konsep edukasi tidak ditemukan pada Learning Mode"

    # 2. Professional Mode
    at_pro = AppTest.from_file(APP_PATH, default_timeout=10)
    at_pro.run()
    at_pro.sidebar.radio(key="ui_mode_selector").set_value("Mode Profesional").run()
    at_pro.session_state[KEY_NAV_PAGE] = "firewall_rules"
    at_pro.run()
    assert not at_pro.exception
    # Panel 'Konsep Penting' harus disembunyikan pada Professional Mode
    pro_mds = [m.value for m in at_pro.markdown if "Konsep Penting" in m.value]
    assert len(pro_mds) == 0, "Panel konsep edukasi seharusnya disembunyikan pada Professional Mode"

    # State identik
    assert at_learn.session_state[KEY_STATE] == at_pro.session_state[KEY_STATE]


def test_ui_workflow_rail_and_flow_next():
    """Menguji bahwa Workflow Rail ter-render di halaman alur kerja dan tombol flow-next berfungsi."""
    at = AppTest.from_file(APP_PATH, default_timeout=10)
    at.run()

    # 1. Buka halaman Network
    at.session_state[KEY_NAV_PAGE] = "network"
    at.run()
    assert not at.exception
    # Periksa keberadaan elemen workflow rail yang AKTUAL (bukan hanya CSS definition)
    # Rail aktual mengandung SEKALIGUS "fw-workflow-rail" (container div) DAN "fw-step-item active" (step aktif)
    rail_actual = [m.value for m in at.markdown if "fw-workflow-rail" in m.value and "fw-step-item active" in m.value]
    assert len(rail_actual) >= 1, "Workflow rail dengan active step tidak ditemukan pada halaman network"

    # Klik tombol flow next menuju firewall_rules
    btn_next = [b for b in at.button if b.key == "btn_flow_next_firewall_rules"]
    assert len(btn_next) == 1, "Tombol flow next ke firewall_rules tidak ditemukan"
    btn_next[0].click().run()
    assert not at.exception
    assert at.session_state[KEY_NAV_PAGE] == "firewall_rules"

    # 2. Periksa workflow rail di firewall_rules aktif di langkah 2
    rail_rules_actual = [m.value for m in at.markdown if "fw-workflow-rail" in m.value and "fw-step-item active" in m.value]
    assert len(rail_rules_actual) >= 1, "Workflow rail dengan active step tidak ditemukan pada halaman firewall_rules"



