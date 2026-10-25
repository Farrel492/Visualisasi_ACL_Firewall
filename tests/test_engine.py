"""Unit tests for Firewall Simulator engine, config service, validation, and alerts."""

from dataclasses import FrozenInstanceError
from datetime import datetime
import pytest

from firewall_sim.config.service import (
    AddRule,
    MoveRule,
    RemoveRule,
    SetDefaultPolicy,
    SetGateway,
    SetInterfaceEnabled,
    SetInterfaceIP,
    ToggleRule,
    update_config,
)
from firewall_sim.core.alerts import AlertPolicy, derive_alerts
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
from firewall_sim.core.validation import validate_topology


FIXED_TIME = datetime(2026, 10, 24, 12, 0, 0)


def test_t01_accept_with_matched_rule(sample_topology: ProjectState):
    """T01: PC A -> Server cocok rule ACCEPT -> Decision ACCEPT, rule tercatat."""
    rule_accept = FirewallRule(
        id="rule_web",
        order=1,
        enabled=True,
        chain=Chain.FORWARD,
        dst_cidr="10.0.0.10/32",
        protocol=Protocol.TCP,
        dst_port="80",
        action=Action.ACCEPT,
        comment="Izinkan HTTP ke Web Server",
    )
    state, err = update_config(sample_topology, AddRule(rule=rule_accept))
    assert not err

    pkt = PacketTest(
        id="pkt_01",
        source_device_id="pc_a",
        destination_device_id="server",
        protocol=Protocol.TCP,
        src_port=49152,
        dst_port=80,
    )

    res = simulate_packet(state, pkt, now=FIXED_TIME)
    assert res.decision == Decision.ACCEPT
    assert res.matched_rule_id == "rule_web"
    assert "rule_web" in res.evaluated_rules
    assert res.config_revision == state.config_revision


def test_t02_drop_with_security_event(sample_topology: ProjectState):
    """T02: PC B -> Server cocok rule DROP -> Decision DROP, SecurityEvent muncul."""
    rule_drop = FirewallRule(
        id="rule_ssh_drop",
        order=1,
        enabled=True,
        chain=Chain.FORWARD,
        protocol=Protocol.TCP,
        dst_port="22",
        action=Action.DROP,
        comment="Blokir SSH",
    )
    state, err = update_config(sample_topology, AddRule(rule=rule_drop))
    assert not err

    pkt = PacketTest(
        id="pkt_02",
        source_device_id="pc_b",
        destination_device_id="server",
        protocol=Protocol.TCP,
        src_port=50000,
        dst_port=22,
    )

    res = simulate_packet(state, pkt, now=FIXED_TIME)
    assert res.decision == Decision.DROP
    assert res.matched_rule_id == "rule_ssh_drop"

    events = derive_alerts(res)
    assert len(events) == 1
    assert events[0].event_type == "FIREWALL_DROP"
    assert events[0].test_id == "pkt_02"
    assert events[0].rule_id == "rule_ssh_drop"
    assert events[0].severity == "info"


def test_t03_first_matching_rule_wins(sample_topology: ProjectState):
    """T03: Dua rule cocok berurutan -> rule pertama (order terkecil) yang menang."""
    rule_1 = FirewallRule(
        id="rule_drop_first",
        order=1,
        enabled=True,
        chain=Chain.FORWARD,
        protocol=Protocol.TCP,
        dst_port="443",
        action=Action.DROP,
    )
    rule_2 = FirewallRule(
        id="rule_accept_second",
        order=2,
        enabled=True,
        chain=Chain.FORWARD,
        protocol=Protocol.TCP,
        dst_port="443",
        action=Action.ACCEPT,
    )
    state, _ = update_config(sample_topology, AddRule(rule=rule_2))
    state, _ = update_config(state, AddRule(rule=rule_1))

    pkt = PacketTest(
        id="pkt_03",
        source_device_id="pc_a",
        destination_device_id="server",
        protocol=Protocol.TCP,
        src_port=40000,
        dst_port=443,
    )

    res = simulate_packet(state, pkt, now=FIXED_TIME)
    assert res.decision == Decision.DROP
    assert res.matched_rule_id == "rule_drop_first"


def test_t04_disabled_rule_ignored(sample_topology: ProjectState):
    """T04: Rule disabled diabaikan dalam evaluasi."""
    rule_disabled = FirewallRule(
        id="rule_disabled_drop",
        order=1,
        enabled=False,
        chain=Chain.FORWARD,
        protocol=Protocol.TCP,
        dst_port="80",
        action=Action.DROP,
    )
    rule_enabled = FirewallRule(
        id="rule_accept",
        order=2,
        enabled=True,
        chain=Chain.FORWARD,
        protocol=Protocol.TCP,
        dst_port="80",
        action=Action.ACCEPT,
    )
    state, _ = update_config(sample_topology, AddRule(rule=rule_disabled))
    state, _ = update_config(state, AddRule(rule=rule_enabled))

    pkt = PacketTest(
        id="pkt_04",
        source_device_id="pc_a",
        destination_device_id="server",
        protocol=Protocol.TCP,
        dst_port=80,
    )

    res = simulate_packet(state, pkt, now=FIXED_TIME)
    assert res.decision == Decision.ACCEPT
    assert res.matched_rule_id == "rule_accept"
    assert "rule_disabled_drop" not in res.evaluated_rules


def test_t05_ip_change_used_in_next_simulation(sample_topology: ProjectState):
    """T05: IP diubah lewat config service -> simulasi berikutnya memakai IP baru."""
    # Ubah IP Server dari 10.0.0.10/24 menjadi 10.0.0.50/24
    state, err = update_config(
        sample_topology,
        SetInterfaceIP(device_id="server", interface_id="if_srv", ipv4_cidr="10.0.0.50/24"),
    )
    assert not err

    # Paket ke IP lama (10.0.0.10) sekarang gagal terjangkau L2 / tidak ada device
    pkt_old = PacketTest(
        id="pkt_old",
        source_device_id="pc_a",
        destination_ip="10.0.0.10",
        protocol=Protocol.TCP,
        dst_port=80,
    )
    res_old = simulate_packet(state, pkt_old, now=FIXED_TIME)
    # 10.0.0.10 ada di subnet router tapi tidak ada host di L2 yang memegang IP ini
    # Di simulator: jika destination_ip bukan device di topologi, diteruskan selama router punya connected net
    # tetapi jika destination_device_id dipakai atau IP baru diuji:
    pkt_new = PacketTest(
        id="pkt_new",
        source_device_id="pc_a",
        destination_device_id="server",
        protocol=Protocol.TCP,
        dst_port=80,
    )
    res_new = simulate_packet(state, pkt_new, now=FIXED_TIME)
    assert res_new.decision == Decision.ACCEPT
    # Memastikan trace mencatat IP baru
    assert any("10.0.0.50" in step.description for step in res_new.trace)


def test_t08_no_route_not_drop(sample_topology: ProjectState):
    """T08: Tidak ada jalur jaringan -> NO_ROUTE, bukan DROP palsu."""
    # Nonaktifkan interface router yang menuju server
    state, err = update_config(
        sample_topology,
        SetInterfaceEnabled(interface_id="r_srv", enabled=False),
    )
    assert not err

    pkt = PacketTest(
        id="pkt_noroute",
        source_device_id="pc_a",
        destination_device_id="server",
        protocol=Protocol.TCP,
        dst_port=80,
    )

    res = simulate_packet(state, pkt, now=FIXED_TIME)
    assert res.decision == Decision.NO_ROUTE
    assert res.decision != Decision.DROP
    assert "down" in res.reason.lower() or "terputus" in res.reason.lower()


def test_t09_invalid_ip_returns_error_and_preserves_state(sample_topology: ProjectState):
    """T09: IP/prefix tidak valid -> error dikembalikan dan state asli tidak berubah."""
    orig_revision = sample_topology.config_revision

    new_state, errors = update_config(
        sample_topology,
        SetInterfaceIP(device_id="pc_a", interface_id="if_pc_a", ipv4_cidr="999.999.1.1/24"),
    )
    assert len(errors) > 0
    assert new_state == sample_topology
    assert new_state.config_revision == orig_revision


def test_t12_drop_event_is_not_labeled_as_attack(sample_topology: ProjectState):
    """T12: Event DROP tidak berlabel serangan / attack (larangan AGENTS.md)."""
    rule_drop = FirewallRule(
        id="rule_drop",
        order=1,
        enabled=True,
        chain=Chain.FORWARD,
        action=Action.DROP,
    )
    state, _ = update_config(sample_topology, AddRule(rule=rule_drop))

    pkt = PacketTest(
        id="pkt_t12",
        source_device_id="pc_a",
        destination_device_id="server",
        protocol=Protocol.TCP,
        dst_port=80,
    )
    res = simulate_packet(state, pkt, now=FIXED_TIME)
    events = derive_alerts(res)
    assert len(events) == 1
    event = events[0]

    assert "serangan" not in event.message.lower()
    assert "attack" not in event.message.lower()
    assert "serangan" not in event.event_type.lower()
    assert "attack" not in event.event_type.lower()
    assert event.event_type == "FIREWALL_DROP"


def test_t13_old_result_preserves_config_revision(sample_topology: ProjectState):
    """T13: Hasil simulasi lama tetap menyimpan config_revision lama setelah config berubah."""
    pkt = PacketTest(
        id="pkt_rev",
        source_device_id="pc_a",
        destination_device_id="server",
        protocol=Protocol.TCP,
        dst_port=80,
    )
    res1 = simulate_packet(sample_topology, pkt, now=FIXED_TIME)
    rev1 = res1.config_revision

    # Mutasi state menaikkan revisi
    rule = FirewallRule(
        id="rule_new",
        order=1,
        enabled=True,
        chain=Chain.FORWARD,
        action=Action.ACCEPT,
    )
    state2, _ = update_config(sample_topology, AddRule(rule=rule))
    assert state2.config_revision == rev1 + 1

    # res1 tetap memegang rev1
    assert res1.config_revision == rev1


def test_determinism_identical_runs(sample_topology: ProjectState):
    """Determinisme: input yang sama menghasilkan output yang identik."""
    pkt = PacketTest(
        id="pkt_det",
        source_device_id="pc_a",
        destination_device_id="server",
        protocol=Protocol.TCP,
        dst_port=80,
    )
    res1 = simulate_packet(sample_topology, pkt, now=FIXED_TIME)
    res2 = simulate_packet(sample_topology, pkt, now=FIXED_TIME)

    assert res1.decision == res2.decision
    assert res1.reason == res2.reason
    assert res1.trace == res2.trace
    assert res1.config_revision == res2.config_revision
    assert res1.timestamp == res2.timestamp


def test_immutability_frozen_dataclass(sample_topology: ProjectState):
    """Imutabilitas: Percobaan mutasi field memicu FrozenInstanceError."""
    with pytest.raises(FrozenInstanceError):
        sample_topology.config_revision = 999  # type: ignore

    pkt = PacketTest(
        id="pkt_mut",
        source_device_id="pc_a",
        destination_device_id="server",
    )
    res = simulate_packet(sample_topology, pkt, now=FIXED_TIME)
    with pytest.raises(FrozenInstanceError):
        res.decision = Decision.DROP  # type: ignore


def test_default_policy_fallback(sample_topology: ProjectState):
    """Default policy berlaku bila tidak ada rule yang cocok."""
    # Ubah default policy chain FORWARD menjadi DROP
    state, err = update_config(
        sample_topology,
        SetDefaultPolicy(chain=Chain.FORWARD, action=Action.DROP),
    )
    assert not err

    pkt = PacketTest(
        id="pkt_def",
        source_device_id="pc_a",
        destination_device_id="server",
        protocol=Protocol.TCP,
        dst_port=80,
    )
    res = simulate_packet(state, pkt, now=FIXED_TIME)
    assert res.decision == Decision.DROP
    assert res.matched_rule_id is None
    assert "Default policy: DROP" in res.reason


def test_port_range_matching(sample_topology: ProjectState):
    """Pengujian pencocokan port range (misal 1000-2000)."""
    rule_range = FirewallRule(
        id="rule_range",
        order=1,
        enabled=True,
        chain=Chain.FORWARD,
        protocol=Protocol.TCP,
        dst_port="1000-2000",
        action=Action.ACCEPT,
    )
    state, _ = update_config(sample_topology, AddRule(rule=rule_range))

    # Port 1500 di dalam rentang
    pkt_in = PacketTest(
        id="p_in",
        source_device_id="pc_a",
        destination_device_id="server",
        protocol=Protocol.TCP,
        dst_port=1500,
    )
    res_in = simulate_packet(state, pkt_in, now=FIXED_TIME)
    assert res_in.decision == Decision.ACCEPT
    assert res_in.matched_rule_id == "rule_range"

    # Port 2500 di luar rentang
    pkt_out = PacketTest(
        id="p_out",
        source_device_id="pc_a",
        destination_device_id="server",
        protocol=Protocol.TCP,
        dst_port=2500,
    )
    res_out = simulate_packet(state, pkt_out, now=FIXED_TIME)
    assert res_out.matched_rule_id != "rule_range"


def test_icmp_without_ports(sample_topology: ProjectState):
    """Pengujian protokol ICMP tanpa port."""
    rule_icmp = FirewallRule(
        id="rule_icmp_block",
        order=1,
        enabled=True,
        chain=Chain.FORWARD,
        protocol=Protocol.ICMP,
        action=Action.DROP,
    )
    state, _ = update_config(sample_topology, AddRule(rule=rule_icmp))

    pkt_icmp = PacketTest(
        id="p_icmp",
        source_device_id="pc_a",
        destination_device_id="server",
        protocol=Protocol.ICMP,
    )
    res = simulate_packet(state, pkt_icmp, now=FIXED_TIME)
    assert res.decision == Decision.DROP
    assert res.matched_rule_id == "rule_icmp_block"


def test_same_subnet_bypass_firewall(sample_topology: ProjectState):
    """Host pada subnet yang sama berkomunikasi lewat switch (L2) tanpa menyentuh firewall."""
    pkt = PacketTest(
        id="p_l2",
        source_device_id="pc_a",
        destination_device_id="pc_b",
        protocol=Protocol.TCP,
        dst_port=445,
    )
    res = simulate_packet(sample_topology, pkt, now=FIXED_TIME)
    assert res.decision == Decision.ACCEPT
    assert res.matched_rule_id is None
    assert "tidak melewati firewall" in res.reason.lower()


def test_gateway_wrong_subnet_detected_in_validation(sample_topology: ProjectState):
    """Gateway yang berada di luar subnet host ditolak oleh validasi konfigurasi."""
    state, errors = update_config(
        sample_topology,
        SetGateway(device_id="pc_a", default_gateway="10.99.99.1"),
    )
    assert len(errors) > 0
    assert any("GATEWAY_NOT_IN_SUBNET" in e for e in errors)
    assert state == sample_topology


def test_router_as_source_unsupported_case(sample_topology: ProjectState):
    """Paket yang bersumber langsung dari router menghasilkan UNSUPPORTED_CASE."""
    pkt = PacketTest(
        id="p_router_src",
        source_device_id="router",
        destination_device_id="server",
    )
    res = simulate_packet(sample_topology, pkt, now=FIXED_TIME)
    assert res.decision == Decision.UNSUPPORTED_CASE
    assert "backlog" in res.reason.lower()


def test_router_input_chain_evaluation(sample_topology: ProjectState):
    """Paket menuju IP interface router dievaluasi pada chain INPUT."""
    rule_input = FirewallRule(
        id="rule_drop_router_mgmt",
        order=1,
        enabled=True,
        chain=Chain.INPUT,
        protocol=Protocol.TCP,
        dst_port=80,
        action=Action.DROP,
    )
    state, _ = update_config(sample_topology, AddRule(rule=rule_input))

    pkt = PacketTest(
        id="p_input",
        source_device_id="pc_a",
        destination_ip="192.168.1.1",  # IP interface router LAN
        protocol=Protocol.TCP,
        dst_port=80,
    )
    res = simulate_packet(state, pkt, now=FIXED_TIME)
    assert res.decision == Decision.DROP
    assert res.matched_rule_id == "rule_drop_router_mgmt"
    assert any("INPUT" in step.description for step in res.trace)


def test_rule_toggle_and_move(sample_topology: ProjectState):
    """Menguji ToggleRule dan MoveRule pada config service."""
    rule = FirewallRule(
        id="r1",
        order=1,
        enabled=True,
        chain=Chain.FORWARD,
        action=Action.DROP,
    )
    state, _ = update_config(sample_topology, AddRule(rule=rule))
    assert state.rules[0].enabled is True

    # Toggle
    state, _ = update_config(state, ToggleRule(rule_id="r1"))
    assert state.rules[0].enabled is False

    # Move order
    state, _ = update_config(state, MoveRule(rule_id="r1", new_order=10))
    assert state.rules[0].order == 10

    # Remove
    state, _ = update_config(state, RemoveRule(rule_id="r1"))
    assert len(state.rules) == 0
