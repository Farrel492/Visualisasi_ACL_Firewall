"""Unit tests for 3D visualization and packet replay frame generation."""

import pytest

from firewall_sim.config.service import AddRule, update_config
from firewall_sim.core.models import (
    Action,
    Chain,
    Decision,
    FirewallRule,
    PacketTest,
    ProjectState,
    Protocol,
)
from firewall_sim.core.simulator import simulate_packet
from firewall_sim.ui.viz3d import build_replay_frames, calculate_3d_positions


def test_t10_3d_replay_drop_terminates_at_router(sample_topology: ProjectState):
    """T10: Untuk keputusan DROP, frame 3D terakhir berada di router dan tidak ada frame setelahnya."""
    rule_drop = FirewallRule(
        id="r_drop_t10",
        order=1,
        enabled=True,
        chain=Chain.FORWARD,
        protocol=Protocol.TCP,
        dst_port="22",
        action=Action.DROP,
    )
    state, _ = update_config(sample_topology, AddRule(rule=rule_drop))

    pkt = PacketTest(
        id="pkt_t10",
        source_device_id="pc_a",
        destination_device_id="server",
        protocol=Protocol.TCP,
        dst_port=22,
    )
    res = simulate_packet(state, pkt)
    assert res.decision == Decision.DROP

    positions = calculate_3d_positions(state)
    frames = build_replay_frames(res, positions)

    assert len(frames) >= 2
    last_frame = frames[-1]

    # Frame terakhir harus berhenti di router
    assert last_frame.device_id == "router"
    # Tidak ada frame lanjutan yang menuju 'server'
    assert not any(f.device_id == "server" for f in frames)


def test_3d_replay_accept_reaches_destination(sample_topology: ProjectState):
    """Untuk keputusan ACCEPT, frame 3D mencapai host tujuan."""
    pkt = PacketTest(
        id="pkt_acc_3d",
        source_device_id="pc_a",
        destination_device_id="server",
        protocol=Protocol.TCP,
        dst_port=80,
    )
    res = simulate_packet(sample_topology, pkt)
    assert res.decision == Decision.ACCEPT

    positions = calculate_3d_positions(sample_topology)
    frames = build_replay_frames(res, positions)

    assert len(frames) >= 3
    last_frame = frames[-1]
    assert last_frame.device_id == "server"
    assert last_frame.action == "ACCEPT"


def test_deterministic_3d_positions(sample_topology: ProjectState):
    """Memastikan koordinat 3D deterministik dan elevasi Z sesuai hierarki perangkat."""
    pos1 = calculate_3d_positions(sample_topology)
    pos2 = calculate_3d_positions(sample_topology)

    assert pos1 == pos2

    # Router di level tertinggi Z
    assert pos1["router"].z > pos1["sw_lan"].z
    # Switch di level menengah Z
    assert pos1["sw_lan"].z > pos1["pc_a"].z
    # Host di ground level (z=0.0)
    assert pos1["pc_a"].z == 0.0
    assert pos1["server"].z == 0.0
