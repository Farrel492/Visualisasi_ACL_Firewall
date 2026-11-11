"""Tes CLI gaya Cisco/Windows (murni, tanpa UI)."""

from firewall_sim.config.cli_parser import parse_and_execute
from firewall_sim.config.ios_cli import CliSession, IosCli, PingOutcome, hostname_of, netmask_to_prefix
from firewall_sim.config.service import update_config
from firewall_sim.core.models import Action, Chain, Decision, FirewallRule, Protocol
from firewall_sim.core.simulator import simulate_packet
from firewall_sim.core.models import PacketTest
from firewall_sim.scenarios.presets import default_lab


class Harness:
    """Menyambungkan IosCli ke ProjectState tanpa Streamlit."""

    def __init__(self, state=None):
        self.state = state or default_lab()

        def apply(cmd):
            new, errors = update_config(self.state, cmd)
            if errors:
                return False, errors
            self.state = new
            return True, []

        def ping(src, dst_id, dst_ip):
            ip = dst_ip
            pkt = PacketTest(id="p", source_device_id=src, destination_device_id=dst_id, destination_ip=ip,
                             protocol=Protocol.ICMP, src_port=None, dst_port=None, config_revision=self.state.config_revision)
            res = simulate_packet(self.state, pkt)
            return PingOutcome(res.decision, res.reason)

        def legacy(line):
            new, out, errors = parse_and_execute(self.state, line)
            if not errors:
                self.state = new
            return out, errors

        self.cli = IosCli(lambda: self.state, apply, ping, legacy)

    def run(self, session, *lines):
        out = []
        for line in lines:
            out += self.cli.execute(session, line)
        return out


def _texts(lines):
    return "\n".join(t for _k, t in lines)


def test_router_modes_and_prompts():
    h = Harness()
    s = CliSession("router")
    assert h.cli.prompt(s) == "Router-Firewall>"
    h.run(s, "enable")
    assert h.cli.prompt(s) == "Router-Firewall#"
    h.run(s, "conf t")
    assert h.cli.prompt(s) == "Router-Firewall(config)#"
    h.run(s, "int fa0/1")
    assert h.cli.prompt(s) == "Router-Firewall(config-if)#"
    h.run(s, "exit")
    assert s.mode == "config"
    h.run(s, "end")
    assert s.mode == "priv"
    h.run(s, "disable")
    assert s.mode == "user"


def test_ip_address_changes_interface_and_revision():
    h = Harness()
    s = CliSession("router")
    rev = h.state.config_revision
    out = h.run(s, "enable", "configure terminal", "interface fa0/1", "ip address 10.0.0.1 255.255.255.0")
    assert not any(k == "err" for k, _ in out), _texts(out)
    router = h.state.get_device("router")
    assert [i.ipv4_cidr for i in router.interfaces if i.name == "Fa0/1"] == ["10.0.0.1/24"]
    assert h.state.config_revision > rev


def test_shutdown_and_no_shutdown():
    h = Harness()
    s = CliSession("router")
    h.run(s, "enable", "conf t", "interface fa0/0", "shutdown")
    assert next(i for i in h.state.get_device("router").interfaces if i.name == "Fa0/0").enabled is False
    h.run(s, "no shutdown")
    assert next(i for i in h.state.get_device("router").interfaces if i.name == "Fa0/0").enabled is True


def test_invalid_input_gives_ios_style_errors():
    h = Harness()
    s = CliSession("router")
    assert "tidak dikenali" in _texts(h.run(s, "asdf"))
    h.run(s, "enable", "conf t", "interface fa0/0")
    assert "tidak valid" in _texts(h.run(s, "ip address 999.1.1.1 255.255.255.0"))
    assert "Netmask tidak valid" in _texts(h.run(s, "ip address 10.0.0.1 255.0.255.0"))
    assert "tidak ditemukan" in _texts(h.run(s, "interface fa9/9"))


def test_user_mode_blocks_privileged_commands():
    h = Harness()
    s = CliSession("router")
    assert "tidak dikenali" in _texts(h.run(s, "configure terminal"))
    assert "tidak dikenali" in _texts(h.run(s, "show running-config"))
    assert s.mode == "user"


def test_abbreviations_and_ambiguity():
    h = Harness()
    s = CliSession("router")
    h.run(s, "en")
    assert s.mode == "priv"
    assert "Building configuration" in _texts(h.run(s, "sh run"))
    assert "Interface" in _texts(h.run(s, "sh ip int br"))


def test_show_running_config_lists_rules_and_policy_on_router():
    h = Harness()
    s = CliSession("router")
    h.run(s, "enable", "conf t", "rule add chain=forward proto=tcp dport=443 action=accept", "end")
    text = _texts(h.run(s, "show running-config"))
    assert "hostname Router-Firewall" in text
    assert "ip address 192.168.1.1 255.255.255.0" in text
    assert "rule 1 forward accept tcp" in text and "dport 443" in text


def test_legacy_rule_command_works_in_config_mode_and_not_user_mode():
    h = Harness()
    s = CliSession("router")
    h.run(s, "enable", "conf t")
    h.run(s, 'rule add chain=forward proto=tcp dport=443 action=accept comment="HTTPS"')
    assert any(r.dst_port == "443" and r.action == Action.ACCEPT for r in h.state.rules)


def test_switch_has_no_ip_address():
    h = Harness()
    s = CliSession("sw_lan")
    out = h.run(s, "enable", "conf t", "interface fa0/5", "ip address 10.1.1.1 255.255.255.0")
    assert "Layer 2" in _texts(out)


def test_host_ipconfig_ping_and_set():
    h = Harness()
    s = CliSession("pc_a")
    assert h.cli.prompt(s) == "C:\\>"
    assert "192.168.1.10" in _texts(h.run(s, "ipconfig"))
    ok = _texts(h.run(s, "ping 10.0.0.10"))
    assert "Reply from 10.0.0.10" in ok and "Lost = 0" in ok
    out = h.run(s, "ipconfig set 192.168.1.50 255.255.255.0 192.168.1.1")
    assert not any(k == "err" for k, _ in out)
    assert h.state.get_device("pc_a").interfaces[0].ipv4_cidr == "192.168.1.50/24"


def test_ping_reports_drop_with_reason_and_cisco_marks():
    h = Harness()
    rule = FirewallRule(id="r1", order=1, enabled=True, chain=Chain.FORWARD, src_cidr="192.168.1.11/32",
                        dst_cidr="10.0.0.10/32", protocol=Protocol.ICMP, action=Action.DROP)
    from firewall_sim.config.service import AddRule
    h.state, _ = update_config(h.state, AddRule(rule=rule))
    host = _texts(h.run(CliSession("pc_b"), "ping 10.0.0.10"))
    assert "Request timed out" in host and "DROP" in host
    s = CliSession("router")
    h.run(s, "enable")
    cisco_ok = _texts(h.run(s, "ping 10.0.0.10"))
    assert "Sending 5" in cisco_ok and "belum didukung" in cisco_ok  # ping dari router belum didukung engine (OUTPUT)


def test_hostname_command_renames_device_and_prompt():
    h = Harness()
    s = CliSession("router")
    h.run(s, "enable", "conf t", "hostname R1")
    assert h.state.get_device("router").name == "R1"
    assert h.cli.prompt(s) == "R1(config)#"


def test_help_lists_mode_specific_commands():
    h = Harness()
    s = CliSession("router")
    assert "enable" in _texts(h.run(s, "?"))
    h.run(s, "enable", "conf t", "interface fa0/0")
    assert "ip address" in _texts(h.run(s, "?"))


def test_helpers():
    assert netmask_to_prefix("255.255.255.0") == 24
    assert netmask_to_prefix("/16") == 16
    assert netmask_to_prefix("255.0.255.0") is None
    assert hostname_of(default_lab().get_device("router")) == "Router-Firewall"


def test_quick_commands_follow_mode():
    h = Harness()
    s = CliSession("router")
    assert "enable" in h.cli.quick_commands(s)
    h.run(s, "enable")
    assert "configure terminal" in h.cli.quick_commands(s)
    h.run(s, "conf t", "interface fa0/0")
    assert "no shutdown" in h.cli.quick_commands(s)
    assert "ipconfig" in h.cli.quick_commands(CliSession("pc_a"))


def test_every_quick_command_runs_without_error_on_every_device_and_mode():
    """Chip contoh harus selalu menjalankan perintah yang valid (tidak ada contoh yang rusak)."""
    from firewall_sim.config.ios_cli import is_host

    base = default_lab()
    for dev in base.devices:
        modes = ["user"] if is_host(dev) else ["user", "priv", "config", "config-if"]
        for mode in modes:
            h = Harness(default_lab())
            s = CliSession(dev.id)
            if mode in ("priv", "config", "config-if"):
                h.run(s, "enable")
            if mode in ("config", "config-if"):
                h.run(s, "configure terminal")
            if mode == "config-if":
                h.run(s, "interface " + dev.interfaces[0].name.lower())
            assert s.mode == mode
            for cmd in h.cli.quick_commands(s):
                fresh = Harness(default_lab())
                fs = CliSession(dev.id, mode, s.iface_id)
                out = fresh.cli.execute(fs, cmd)
                errs = [t for k, t in out if k == "err" and not t.startswith("U") and not t.startswith("Request") and not t.startswith("Destination")]
                errs = [e for e in errs if e.startswith("%")]
                assert not errs, f"{dev.name} [{mode}] '{cmd}' -> {errs}"
