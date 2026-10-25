"""Unit tests for traffic log aggregation, analytics, and alerting logic."""

from datetime import datetime, timedelta
import pytest

from firewall_sim.config.service import AddRule, update_config
from firewall_sim.core.alerts import derive_alerts
from firewall_sim.core.analytics import (
    create_log_entry,
    filter_traffic,
    summarize_traffic,
)
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


FIXED_TIME = datetime(2026, 10, 24, 12, 0, 0)


def test_traffic_log_entry_creation_and_t13_versioning(sample_topology: ProjectState):
    """T13: Entri traffic log lama tetap menyimpan config_revision lama setelah config berubah."""
    pkt = PacketTest(
        id="pkt_log_1",
        source_device_id="pc_a",
        destination_device_id="server",
        protocol=Protocol.TCP,
        dst_port=80,
    )
    res = simulate_packet(sample_topology, pkt, now=FIXED_TIME)
    log_entry_1 = create_log_entry(pkt, res)

    assert log_entry_1.config_revision == sample_topology.config_revision
    assert log_entry_1.decision == Decision.ACCEPT

    # Mutasi state menaikkan config_revision
    rule = FirewallRule(
        id="r_new",
        order=1,
        enabled=True,
        chain=Chain.FORWARD,
        action=Action.ACCEPT,
    )
    new_state, _ = update_config(sample_topology, AddRule(rule=rule))
    assert new_state.config_revision == sample_topology.config_revision + 1

    # Log lama tidak terpengaruh revisi baru
    assert log_entry_1.config_revision == sample_topology.config_revision


def test_summarize_traffic_statistics(sample_topology: ProjectState):
    """Menguji kalkulasi statistik agregasi (total, ACCEPT, DROP, NO_ROUTE)."""
    # 1. Packet ACCEPT
    pkt1 = PacketTest(id="p1", source_device_id="pc_a", destination_device_id="server", protocol=Protocol.TCP, dst_port=80)
    res1 = simulate_packet(sample_topology, pkt1, now=FIXED_TIME)

    # 2. Packet DROP
    rule_drop = FirewallRule(id="r_drp", order=1, enabled=True, chain=Chain.FORWARD, protocol=Protocol.TCP, dst_port=22, action=Action.DROP)
    state_drop, _ = update_config(sample_topology, AddRule(rule=rule_drop))
    pkt2 = PacketTest(id="p2", source_device_id="pc_a", destination_device_id="server", protocol=Protocol.TCP, dst_port=22)
    res2 = simulate_packet(state_drop, pkt2, now=FIXED_TIME)

    logs = [create_log_entry(pkt1, res1), create_log_entry(pkt2, res2)]
    summary = summarize_traffic(logs)

    assert summary["total"] == 2
    assert summary["ACCEPT"] == 1
    assert summary["DROP"] == 1
    assert summary["NO_ROUTE"] == 0


def test_filter_traffic_by_decision_and_target(sample_topology: ProjectState):
    """Menguji filtering traffic log berdasarkan keputusan dan IP/Device."""
    pkt1 = PacketTest(id="p1", source_device_id="pc_a", destination_device_id="server", protocol=Protocol.TCP, dst_port=80)
    res1 = simulate_packet(sample_topology, pkt1, now=FIXED_TIME)

    pkt2 = PacketTest(id="p2", source_device_id="pc_a", destination_device_id="pc_b", protocol=Protocol.TCP, dst_port=445)
    res2 = simulate_packet(sample_topology, pkt2, now=FIXED_TIME + timedelta(minutes=1))

    logs = [create_log_entry(pkt1, res1), create_log_entry(pkt2, res2)]

    # Filter target "server"
    f_server = filter_traffic(logs, ip_or_device="server")
    assert len(f_server) == 1
    assert f_server[0].id == "log_p1"

    # Filter target "pc_b"
    f_pcb = filter_traffic(logs, ip_or_device="pc_b")
    assert len(f_pcb) == 1
    assert f_pcb[0].id == "log_p2"

    # Filter decision DROP (tidak ada)
    f_drop = filter_traffic(logs, decision=Decision.DROP)
    assert len(f_drop) == 0


def test_t12_security_event_drop_without_attack_label(sample_topology: ProjectState):
    """T12: derive_alerts untuk DROP tidak menghasilkan label 'attack' atau 'serangan'."""
    rule_drop = FirewallRule(id="r_drp", order=1, enabled=True, chain=Chain.FORWARD, action=Action.DROP)
    state, _ = update_config(sample_topology, AddRule(rule=rule_drop))

    pkt = PacketTest(id="p_t12", source_device_id="pc_a", destination_device_id="server")
    res = simulate_packet(state, pkt, now=FIXED_TIME)
    events = derive_alerts(res)

    assert len(events) == 1
    ev = events[0]
    assert ev.event_type == "FIREWALL_DROP"
    assert "attack" not in ev.message.lower()
    assert "serangan" not in ev.message.lower()
