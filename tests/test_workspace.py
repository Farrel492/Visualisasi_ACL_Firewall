"""Tes penyimpanan workspace: pekerjaan harus selamat dari refresh halaman."""

from datetime import datetime
from pathlib import Path

from streamlit.testing.v1 import AppTest

from firewall_sim.core.alerts import AlertPolicy, derive_alerts
from firewall_sim.core.analytics import create_log_entry
from firewall_sim.core.models import PacketTest, Protocol
from firewall_sim.core.simulator import simulate_packet
from firewall_sim.scenarios.presets import default_lab
from firewall_sim.ui import topo, workspace as ws


APP_PATH = str(Path(__file__).parent.parent / "app.py")


def _sample_snapshot():
    state = default_lab()
    pkt = PacketTest(
        id="p1", source_device_id="pc_a", destination_device_id="server",
        destination_ip="10.0.0.10", protocol=Protocol.TCP, src_port=49152, dst_port=80,
        timestamp=datetime(2026, 10, 29, 10, 0, 0), config_revision=state.config_revision,
    )
    res = simulate_packet(state, pkt)
    return {
        "state": state,
        "pairs": [(pkt, res)],
        "logs": [create_log_entry(pkt, res)],
        "events": list(derive_alerts(res, AlertPolicy(highlight_drop=True))),
        "cli_log": [("show rules", "ok", [])],
        "mode": "Professional",
        "layout": {"pc_a": [120.0, 150.0]},
        "cables": {"link_r_srv": "se"},
    }


def test_snapshot_round_trip_preserves_everything():
    snap = _sample_snapshot()
    token = ws.new_token()
    assert ws.write_snapshot(token, snap)
    back, errors = ws.read_snapshot(token)
    assert errors == []
    assert back["state"] == snap["state"]
    assert back["pairs"] == snap["pairs"]
    assert back["logs"] == snap["logs"]
    assert back["events"] == snap["events"]
    assert back["mode"] == "Professional"
    assert back["layout"] == snap["layout"]
    assert back["cables"] == snap["cables"]


def test_corrupt_workspace_file_is_reported_not_crashing():
    token = ws.new_token()
    ws.workspace_path(token).write_text("{bukan json", encoding="utf-8")
    snap, errors = ws.read_snapshot(token)
    assert snap is None and errors


def test_invalid_token_is_rejected():
    assert not ws.is_valid_token("../etc/passwd")
    assert not ws.is_valid_token("")
    assert ws.is_valid_token(ws.new_token())


def test_refresh_restores_work_via_url_token():
    """Simulasi refresh: sesi baru dengan token URL yang sama memulihkan perangkat dan rule."""
    first = AppTest.from_file(APP_PATH, default_timeout=30)
    first.run()
    assert not first.exception
    token = first.query_params["w"]
    assert ws.is_valid_token(token if isinstance(token, str) else token[0])
    token = token if isinstance(token, str) else token[0]

    # muat demo lalu tunggu penyimpanan
    demo = [b for b in first.button if "demo" in (b.label or "").lower()]
    assert demo, "tombol demo tidak ditemukan"
    demo[0].click()
    first.run()
    assert not first.exception

    second = AppTest.from_file(APP_PATH, default_timeout=30)
    second.query_params["w"] = token
    second.run()
    assert not second.exception
    restored = second.session_state["fw_sim_project_state"]
    assert len(restored.rules) == 2
    assert len(second.session_state["fw_sim_pairs"]) == 2


def test_layout_resolution_keeps_saved_positions_and_places_new_devices():
    state = default_lab()
    layout = topo.resolve_layout(state, {"pc_a": [200.0, 100.0]})
    assert layout["pc_a"] == [200.0, 100.0]
    assert set(layout) == {d.id for d in state.devices}
