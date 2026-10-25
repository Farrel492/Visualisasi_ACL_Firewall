"""Domain models and immutable entities for Firewall Simulator core.

ATURAN ARSITEKTUR:
- Murni Python standard library (tanpa dependensi UI/Streamlit).
- Semua model merupakan frozen dataclass dan koleksi berupa tuple agar immutable.
- State mutasi selalu menghasilkan objek ProjectState baru dengan kenaikan config_revision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Tuple


class DeviceType(str, Enum):
    PC = "pc"
    SERVER = "server"
    ROUTER = "router"
    SWITCH = "switch"


class Chain(str, Enum):
    INPUT = "input"
    FORWARD = "forward"
    OUTPUT = "output"


class Protocol(str, Enum):
    ANY = "any"
    TCP = "tcp"
    UDP = "udp"
    ICMP = "icmp"


class Action(str, Enum):
    ACCEPT = "accept"
    DROP = "drop"


class Decision(str, Enum):
    ACCEPT = "ACCEPT"
    DROP = "DROP"
    NO_ROUTE = "NO_ROUTE"
    INVALID_CONFIG = "INVALID_CONFIG"
    UNSUPPORTED_CASE = "UNSUPPORTED_CASE"


@dataclass(frozen=True)
class Interface:
    id: str
    device_id: str
    name: str
    ipv4_cidr: Optional[str] = None  # None untuk interface switch (L2)
    enabled: bool = True


@dataclass(frozen=True)
class Device:
    id: str
    name: str
    type: DeviceType
    interfaces: Tuple[Interface, ...] = ()
    default_gateway: Optional[str] = None  # Relevan untuk host (PC/Server)


@dataclass(frozen=True)
class Link:
    id: str
    interface_a: str  # ID interface A
    interface_b: str  # ID interface B
    enabled: bool = True


@dataclass(frozen=True)
class FirewallRule:
    id: str
    order: int
    enabled: bool
    chain: Chain
    src_cidr: Optional[str] = None  # None atau '0.0.0.0/0' / 'any'
    dst_cidr: Optional[str] = None
    protocol: Protocol = Protocol.ANY
    src_port: Optional[str] = None  # Single port '80' atau range '1000-2000'
    dst_port: Optional[str] = None
    action: Action = Action.DROP
    comment: str = ""
    counter: int = 0  # Counter paket yang cocok


@dataclass(frozen=True)
class PacketTest:
    id: str
    source_device_id: str
    destination_device_id: Optional[str] = None
    destination_ip: Optional[str] = None
    protocol: Protocol = Protocol.TCP
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    timestamp: Optional[datetime] = None
    config_revision: int = 0


@dataclass(frozen=True)
class TraceStep:
    step_number: int
    device_id: str
    description: str
    rule_id: Optional[str] = None
    action: Optional[str] = None
    link_id: Optional[str] = None


@dataclass(frozen=True)
class SimulationResult:
    test_id: str
    decision: Decision
    reason: str
    matched_rule_id: Optional[str]
    trace: Tuple[TraceStep, ...]
    config_revision: int
    timestamp: datetime
    evaluated_rules: Tuple[str, ...] = ()


@dataclass(frozen=True)
class SecurityEvent:
    id: str
    test_id: str
    event_type: str  # e.g. "FIREWALL_DROP"
    severity: str    # "info", "warning", "high"
    timestamp: datetime
    message: str
    device_id: Optional[str] = None
    rule_id: Optional[str] = None
    acknowledged: bool = False


@dataclass(frozen=True)
class AuditEntry:
    timestamp: datetime
    source: str  # "GUI", "CLI", "TEST"
    summary: str


@dataclass(frozen=True)
class ProjectState:
    devices: Tuple[Device, ...] = ()
    links: Tuple[Link, ...] = ()
    rules: Tuple[FirewallRule, ...] = ()
    config_revision: int = 0
    default_policies: Tuple[Tuple[Chain, Action], ...] = (
        (Chain.INPUT, Action.ACCEPT),
        (Chain.FORWARD, Action.ACCEPT),
        (Chain.OUTPUT, Action.ACCEPT),
    )
    scenario_metadata: Tuple[Tuple[str, str], ...] = ()
    audit_log: Tuple[AuditEntry, ...] = ()

    def get_default_policy(self, chain: Chain) -> Action:
        for c, a in self.default_policies:
            if c == chain:
                return a
        return Action.ACCEPT

    def get_device(self, device_id: str) -> Optional[Device]:
        for d in self.devices:
            if d.id == device_id:
                return d
        return None

    def get_interface(self, interface_id: str) -> Optional[Interface]:
        for d in self.devices:
            for iface in d.interfaces:
                if iface.id == interface_id:
                    return iface
        return None
