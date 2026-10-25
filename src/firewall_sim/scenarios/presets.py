"""Preset scenarios and Learning Lab templates for Firewall Simulator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from firewall_sim.core.models import (
    Action,
    Chain,
    Decision,
    Device,
    DeviceType,
    FirewallRule,
    Interface,
    Link,
    PacketTest,
    ProjectState,
    Protocol,
)


@dataclass(frozen=True)
class ScenarioInfo:
    id: str
    title: str
    objective: str
    steps: Tuple[str, ...]
    expected_result: str
    expected_decision: Decision
    factory: Callable[[], ProjectState]
    test_packet: PacketTest


def default_lab() -> ProjectState:
    """Preset topologi lab standar:

    - PC A (192.168.1.10/24), PC B (192.168.1.11/24), Switch LAN
    - Router Firewall: LAN (192.168.1.1/24), SRV (10.0.0.1/24)
    - Web Server (10.0.0.10/24)
    """
    pc_a = Device(
        id="pc_a",
        name="PC A",
        type=DeviceType.PC,
        interfaces=(
            Interface(id="if_pc_a", device_id="pc_a", name="eth0", ipv4_cidr="192.168.1.10/24", enabled=True),
        ),
        default_gateway="192.168.1.1",
    )

    pc_b = Device(
        id="pc_b",
        name="PC B",
        type=DeviceType.PC,
        interfaces=(
            Interface(id="if_pc_b", device_id="pc_b", name="eth0", ipv4_cidr="192.168.1.11/24", enabled=True),
        ),
        default_gateway="192.168.1.1",
    )

    sw_lan = Device(
        id="sw_lan",
        name="Switch LAN",
        type=DeviceType.SWITCH,
        interfaces=(
            Interface(id="sw_p1", device_id="sw_lan", name="port1", ipv4_cidr=None, enabled=True),
            Interface(id="sw_p2", device_id="sw_lan", name="port2", ipv4_cidr=None, enabled=True),
            Interface(id="sw_p3", device_id="sw_lan", name="port3", ipv4_cidr=None, enabled=True),
        ),
    )

    router = Device(
        id="router",
        name="Router Firewall",
        type=DeviceType.ROUTER,
        interfaces=(
            Interface(id="r_lan", device_id="router", name="eth0", ipv4_cidr="192.168.1.1/24", enabled=True),
            Interface(id="r_srv", device_id="router", name="eth1", ipv4_cidr="10.0.0.1/24", enabled=True),
        ),
    )

    server = Device(
        id="server",
        name="Web Server",
        type=DeviceType.SERVER,
        interfaces=(
            Interface(id="if_srv", device_id="server", name="eth0", ipv4_cidr="10.0.0.10/24", enabled=True),
        ),
        default_gateway="10.0.0.1",
    )

    links = (
        Link(id="link_pca_sw", interface_a="if_pc_a", interface_b="sw_p1", enabled=True),
        Link(id="link_pcb_sw", interface_a="if_pc_b", interface_b="sw_p2", enabled=True),
        Link(id="link_r_sw", interface_a="r_lan", interface_b="sw_p3", enabled=True),
        Link(id="link_r_srv", interface_a="r_srv", interface_b="if_srv", enabled=True),
    )

    return ProjectState(
        devices=(pc_a, pc_b, sw_lan, router, server),
        links=links,
        rules=(),
        config_revision=1,
        default_policies=(
            (Chain.INPUT, Action.ACCEPT),
            (Chain.FORWARD, Action.ACCEPT),
            (Chain.OUTPUT, Action.ACCEPT),
        ),
        scenario_metadata=(("name", "Default Topology Lab"),),
        audit_log=(),
    )


def empty_project() -> ProjectState:
    """Preset proyek kosong minimal yang memenuhi syarat topologi MVP (tepat 1 router)."""
    router = Device(
        id="router",
        name="Router Firewall",
        type=DeviceType.ROUTER,
        interfaces=(
            Interface(id="r_eth0", device_id="router", name="eth0", ipv4_cidr="192.168.1.1/24", enabled=True),
        ),
    )
    return ProjectState(
        devices=(router,),
        links=(),
        rules=(),
        config_revision=1,
        default_policies=(
            (Chain.INPUT, Action.ACCEPT),
            (Chain.FORWARD, Action.ACCEPT),
            (Chain.OUTPUT, Action.ACCEPT),
        ),
        scenario_metadata=(("name", "Empty Project"),),
        audit_log=(),
    )


# 4 PRESET SCENARIOS LENGKAP
def scenario_web_allow() -> ProjectState:
    """Skenario 1: PC diizinkan mengakses Web Server (HTTP port 80)."""
    base = default_lab()
    rule_web = FirewallRule(
        id="rule_allow_web",
        order=1,
        enabled=True,
        chain=Chain.FORWARD,
        dst_cidr="10.0.0.10/32",
        protocol=Protocol.TCP,
        dst_port="80",
        action=Action.ACCEPT,
        comment="Izinkan HTTP ke Web Server",
    )
    return ProjectState(
        devices=base.devices,
        links=base.links,
        rules=(rule_web,),
        config_revision=1,
        default_policies=base.default_policies,
        scenario_metadata=(
            ("id", "scen_web_allow"),
            ("name", "PC Diizinkan ke Web Server"),
        ),
        audit_log=base.audit_log,
    )


def scenario_ssh_blocked() -> ProjectState:
    """Skenario 2: PC diblokir mengakses SSH (Port 22) dengan Policy Forward DROP."""
    base = default_lab()
    # Menunjukkan default policy forward=drop sebagai implementasi explicit implicit-deny
    rule_web = FirewallRule(
        id="rule_web_only",
        order=1,
        enabled=True,
        chain=Chain.FORWARD,
        dst_cidr="10.0.0.10/32",
        protocol=Protocol.TCP,
        dst_port="80",
        action=Action.ACCEPT,
        comment="Hanya izinkan HTTP",
    )
    return ProjectState(
        devices=base.devices,
        links=base.links,
        rules=(rule_web,),
        config_revision=1,
        default_policies=(
            (Chain.INPUT, Action.ACCEPT),
            (Chain.FORWARD, Action.DROP),  # Default policy DROP
            (Chain.OUTPUT, Action.ACCEPT),
        ),
        scenario_metadata=(
            ("id", "scen_ssh_blocked"),
            ("name", "PC Diblokir SSH (Default Policy DROP)"),
        ),
        audit_log=base.audit_log,
    )


def scenario_colliding_rules() -> ProjectState:
    """Skenario 3: Aturan Bertabrakan (Dua rule cocok, urutan/order menentukan hasil)."""
    base = default_lab()
    rule_drop_first = FirewallRule(
        id="rule_drop_https",
        order=1,
        enabled=True,
        chain=Chain.FORWARD,
        protocol=Protocol.TCP,
        dst_port="443",
        action=Action.DROP,
        comment="Aturan #1: Blokir HTTPS",
    )
    rule_allow_second = FirewallRule(
        id="rule_allow_https",
        order=2,
        enabled=True,
        chain=Chain.FORWARD,
        protocol=Protocol.TCP,
        dst_port="443",
        action=Action.ACCEPT,
        comment="Aturan #2: Izinkan HTTPS (Tertutup Aturan #1)",
    )
    return ProjectState(
        devices=base.devices,
        links=base.links,
        rules=(rule_drop_first, rule_allow_second),
        config_revision=1,
        default_policies=base.default_policies,
        scenario_metadata=(
            ("id", "scen_colliding"),
            ("name", "Aturan Bertabrakan (First Matching Rule Wins)"),
        ),
        audit_log=base.audit_log,
    )


def scenario_wrong_gateway() -> ProjectState:
    """Skenario 4: Salah Subnet / Link Gateway Terputus (Hasil NO_ROUTE)."""
    base = default_lab()
    # Buat link router LAN ke switch nonaktif (terputus secara fisik/L2)
    new_links = list(base.links)
    for idx, l in enumerate(new_links):
        if l.id == "link_r_sw":
            new_links[idx] = Link(
                id=l.id,
                interface_a=l.interface_a,
                interface_b=l.interface_b,
                enabled=False,  # Link putus
            )
    return ProjectState(
        devices=base.devices,
        links=tuple(new_links),
        rules=(),
        config_revision=1,
        default_policies=base.default_policies,
        scenario_metadata=(
            ("id", "scen_wrong_gw"),
            ("name", "Salah Subnet / Gateway Terputus"),
        ),
        audit_log=base.audit_log,
    )


def list_scenarios() -> List[ScenarioInfo]:
    """Mengembalikan daftar 4 preset skenario lengkap beserta metadata instruksional."""
    return [
        ScenarioInfo(
            id="scen_web_allow",
            title="1. PC Diizinkan ke Web Server",
            objective="Memverifikasi paket HTTP (TCP port 80) dari PC A lolos aturan firewall menuju Web Server.",
            steps=(
                "Periksa tabel firewall: terdapat rule ACCEPT untuk port 80.",
                "Inisiasi paket dari PC A (192.168.1.10) ke Web Server (10.0.0.10) port 80.",
                "Amati status keputusan ACCEPT dan matched rule 'rule_allow_web'.",
            ),
            expected_result="Paket berhasil melintasi router firewall dan berstatus ACCEPT.",
            expected_decision=Decision.ACCEPT,
            factory=scenario_web_allow,
            test_packet=PacketTest(
                id="pkt_test_scen1",
                source_device_id="pc_a",
                destination_device_id="server",
                protocol=Protocol.TCP,
                dst_port=80,
            ),
        ),
        ScenarioInfo(
            id="scen_ssh_blocked",
            title="2. PC Diblokir SSH (Default Policy DROP)",
            objective="Memverifikasi paket SSH (TCP port 22) ditolak oleh kebijakan default forward=drop.",
            steps=(
                "Default policy chain FORWARD diset ke DROP.",
                "Kirim paket SSH (port 22) dari PC A ke Web Server.",
                "Amati paket dihentikan di router firewall dengan status DROP.",
            ),
            expected_result="Paket di-DROP oleh Default Policy router dan menghasilkan SecurityEvent.",
            expected_decision=Decision.DROP,
            factory=scenario_ssh_blocked,
            test_packet=PacketTest(
                id="pkt_test_scen2",
                source_device_id="pc_a",
                destination_device_id="server",
                protocol=Protocol.TCP,
                dst_port=22,
            ),
        ),
        ScenarioInfo(
            id="scen_colliding",
            title="3. Aturan Bertabrakan (First Match Wins)",
            objective="Memverifikasi prinsip first-matching terminal action saat dua rule cocok berurutan.",
            steps=(
                "Rule #1 (order 1) me-DROP HTTPS port 443.",
                "Rule #2 (order 2) meng-ACCEPT HTTPS port 443.",
                "Jalankan paket HTTPS: Rule #1 yang dievaluasi pertama kali menentukan hasil akhir.",
            ),
            expected_result="Paket di-DROP oleh Rule #1 karena memiliki order lebih kecil.",
            expected_decision=Decision.DROP,
            factory=scenario_colliding_rules,
            test_packet=PacketTest(
                id="pkt_test_scen3",
                source_device_id="pc_a",
                destination_device_id="server",
                protocol=Protocol.TCP,
                dst_port=443,
            ),
        ),
        ScenarioInfo(
            id="scen_wrong_gw",
            title="4. Salah Subnet / Gateway Terputus",
            objective="Memverifikasi bahwa kegagalan perutean menghasilkan NO_ROUTE, BUKAN DROP palsu.",
            steps=(
                "Link penghubung antara gateway router dan switch dalam keadaan down/terputus.",
                "Kirim paket dari PC A ke Web Server di subnet yang berbeda.",
                "Amati sistem melaporkan NO_ROUTE, bukan penolakan kebijakan (DROP).",
            ),
            expected_result="Hasil pengujian adalah NO_ROUTE dengan pesan rute gateway terputus.",
            expected_decision=Decision.NO_ROUTE,
            factory=scenario_wrong_gateway,
            test_packet=PacketTest(
                id="pkt_test_scen4",
                source_device_id="pc_a",
                destination_device_id="server",
                protocol=Protocol.TCP,
                dst_port=80,
            ),
        ),
    ]
