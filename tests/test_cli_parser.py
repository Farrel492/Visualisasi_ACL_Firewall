"""Unit tests for restricted CLI parser and commands."""

from datetime import datetime
import pytest

from firewall_sim.config.cli_parser import parse_and_execute
from firewall_sim.config.service import AddRule, ToggleRule, update_config
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


def test_t06_cli_adds_rule_readable_by_state(sample_topology: ProjectState):
    """T06: CLI menambah rule -> terbaca di state yang dipakai GUI & engine."""
    cmd = 'rule add chain=forward proto=tcp dport=80 action=accept comment="Web traffic"'
    new_state, out, errors = parse_and_execute(sample_topology, cmd, now=FIXED_TIME)

    assert not errors
    assert len(new_state.rules) == 1
    rule = new_state.rules[0]
    assert rule.chain == Chain.FORWARD
    assert rule.protocol == Protocol.TCP
    assert rule.dst_port == "80"
    assert rule.action == Action.ACCEPT
    assert rule.comment == "Web traffic"

    # Engine membaca rule yang ditambahkan CLI
    pkt = PacketTest(
        id="pkt_cli",
        source_device_id="pc_a",
        destination_device_id="server",
        protocol=Protocol.TCP,
        dst_port=80,
    )
    res = simulate_packet(new_state, pkt, now=FIXED_TIME)
    assert res.decision == Decision.ACCEPT
    assert res.matched_rule_id == rule.id


def test_t07_gui_style_mutation_read_by_cli_show(sample_topology: ProjectState):
    """T07: Mutasi GUI (AddRule/ToggleRule) -> CLI `show rules` menampilkan nilai baru."""
    rule = FirewallRule(
        id="r_gui_drop",
        order=1,
        enabled=True,
        chain=Chain.FORWARD,
        protocol=Protocol.TCP,
        dst_port="22",
        action=Action.DROP,
    )
    state, err = update_config(sample_topology, AddRule(rule=rule, source="GUI"))
    assert not err

    _, out, errors = parse_and_execute(state, "show rules forward")
    assert not errors
    assert "r_gui_drop" in out
    assert "DROP" in out
    assert "enabled" in out

    # Toggle via GUI
    state2, _ = update_config(state, ToggleRule(rule_id="r_gui_drop", source="GUI"))
    _, out2, _ = parse_and_execute(state2, "show rules")
    assert "disabled" in out2


def test_t14_malicious_input_and_unknown_commands_safe(sample_topology: ProjectState):
    """T14: Input berbahaya dan perintah tak dikenal ditolak aman tanpa eksekusi shell."""
    orig_rev = sample_topology.config_revision

    malicious_inputs = [
        "; rm -rf /",
        "__import__('os').system('echo pwned')",
        "eval('1 + 1')",
        "`ls -la`",
        "$(cat /etc/passwd)",
        "cmd.exe /c dir",
        "unknown_command foo bar",
    ]

    for line in malicious_inputs:
        state, out, errors = parse_and_execute(sample_topology, line, now=FIXED_TIME)
        # Harus mengembalikan error dan saran help
        assert len(errors) > 0, f"Seharusnya error untuk: {line}"
        assert "help" in errors[0].lower()
        # State asli tidak berubah sama sekali
        assert state == sample_topology
        assert state.config_revision == orig_rev


def test_cli_rule_management_commands(sample_topology: ProjectState):
    """Menguji rule move, enable, disable, dan remove pada CLI."""
    # Add rule
    s1, _, _ = parse_and_execute(sample_topology, "rule add chain=forward action=drop", now=FIXED_TIME)
    rule_id = s1.rules[0].id

    # Move
    s2, out_move, err_move = parse_and_execute(s1, f"rule move {rule_id} 50", now=FIXED_TIME)
    assert not err_move
    assert s2.rules[0].order == 50

    # Disable
    s3, _, _ = parse_and_execute(s2, f"rule disable {rule_id}", now=FIXED_TIME)
    assert s3.rules[0].enabled is False

    # Enable
    s4, _, _ = parse_and_execute(s3, f"rule enable {rule_id}", now=FIXED_TIME)
    assert s4.rules[0].enabled is True

    # Remove
    s5, _, _ = parse_and_execute(s4, f"rule remove {rule_id}", now=FIXED_TIME)
    assert len(s5.rules) == 0


def test_cli_access_list_translation(sample_topology: ProjectState):
    """Menguji translasi access-list Cisco-style ke FirewallRule kanonik."""
    cmd = "access-list permit tcp any 10.0.0.10 eq 80"
    new_state, out, errors = parse_and_execute(sample_topology, cmd, now=FIXED_TIME)

    assert not errors
    assert "[CATATAN]" in out
    assert "implicit deny Cisco TIDAK diterapkan" in out
    assert len(new_state.rules) == 1
    r = new_state.rules[0]
    assert r.action == Action.ACCEPT
    assert r.protocol == Protocol.TCP
    assert r.dst_cidr == "10.0.0.10/32"
    assert r.dst_port == "80"


def test_cli_test_command_matches_simulate_packet(sample_topology: ProjectState):
    """Perintah 'test' di CLI memberikan hasil yang konsisten dengan simulate_packet."""
    cli_line = "test pc_a server tcp 80"
    state, out, errors = parse_and_execute(sample_topology, cli_line, now=FIXED_TIME)
    assert not errors
    assert "ACCEPT" in out
    assert "Trace Langkah" in out

    pkt = PacketTest(
        id="direct_pkt",
        source_device_id="pc_a",
        destination_device_id="server",
        protocol=Protocol.TCP,
        dst_port=80,
    )
    res = simulate_packet(sample_topology, pkt, now=FIXED_TIME)
    assert res.decision.value in out


def test_cli_show_commands(sample_topology: ProjectState):
    """Menguji output berbagai perintah show di CLI."""
    for target in ["running-config", "interfaces", "rules", "policy", "audit", "revision", "links"]:
        _, out, errors = parse_and_execute(sample_topology, f"show {target}")
        assert not errors
        assert len(out) > 0
