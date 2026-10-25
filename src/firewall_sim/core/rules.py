"""Firewall rule evaluation engine.

ATURAN ARSITEKTUR:
- Evaluasi berurutan berdasarkan atribut 'order' (ascending).
- Hanya rule dengan 'enabled=True' yang dievaluasi.
- First matching rule wins (terminal action).
- Port hanya relevan untuk TCP dan UDP; ICMP tidak memakai port.
- Jika tidak ada rule yang cocok, terapkan default policy chain yang bersangkutan.
"""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
from typing import List, Optional, Tuple, Union

from firewall_sim.core.models import (
    Action,
    Chain,
    FirewallRule,
    PacketTest,
    Protocol,
)


@dataclass(frozen=True)
class RuleEvaluationResult:
    action: Action
    matched_rule: Optional[FirewallRule]
    evaluated_rule_ids: Tuple[str, ...]
    reason: str


def _match_ip(ip_str: str, cidr_filter: Optional[str]) -> bool:
    """Mencocokkan IP dengan filter CIDR."""
    if not cidr_filter or cidr_filter.strip().lower() in ("any", "0.0.0.0/0", ""):
        return True
    try:
        net = ipaddress.ip_network(cidr_filter.strip(), strict=False)
        ip = ipaddress.ip_address(ip_str)
        return ip in net
    except ValueError:
        return False


def _match_port(packet_port: Optional[int], port_filter: Optional[Union[str, int]]) -> bool:
    """Mencocokkan port paket dengan port atau port range pada rule."""
    if port_filter is None:
        return True
    port_filter_str = str(port_filter).strip()
    if not port_filter_str or port_filter_str.lower() in ("any", ""):
        return True
    if packet_port is None:
        return False

    if "-" in port_filter_str:
        parts = port_filter_str.split("-")
        if len(parts) == 2:
            try:
                start_p = int(parts[0].strip())
                end_p = int(parts[1].strip())
                return start_p <= packet_port <= end_p
            except ValueError:
                return False
    else:
        try:
            return packet_port == int(port_filter_str)
        except ValueError:
            return False
    return False


def matches_rule(rule: FirewallRule, src_ip: str, dst_ip: str, packet: PacketTest) -> bool:
    """Memeriksa apakah satu rule cocok dengan parameter paket."""
    # 1. Cek Protokol
    if rule.protocol != Protocol.ANY and rule.protocol != packet.protocol:
        return False

    # 2. Cek CIDR Sumber dan Tujuan
    if not _match_ip(src_ip, rule.src_cidr):
        return False
    if not _match_ip(dst_ip, rule.dst_cidr):
        return False

    # 3. Cek Port (hanya relevan jika protokol TCP/UDP)
    if packet.protocol in (Protocol.TCP, Protocol.UDP):
        if not _match_port(packet.src_port, rule.src_port):
            return False
        if not _match_port(packet.dst_port, rule.dst_port):
            return False
    elif packet.protocol == Protocol.ICMP:
        # Untuk ICMP, port rule diabaikan jika diisi, atau rule yang menspesifikasikan port tidak cocok
        if rule.src_port or rule.dst_port:
            return False

    return True


def evaluate_chain(
    rules: Tuple[FirewallRule, ...],
    chain: Chain,
    src_ip: str,
    dst_ip: str,
    packet: PacketTest,
    default_policy: Action = Action.ACCEPT,
) -> RuleEvaluationResult:
    """Mengevaluasi rule dalam chain tertentu secara berurutan."""
    # Filter rule untuk chain yang cocok dan berstatus enabled, lalu urutkan berdasarkan order
    candidate_rules = sorted(
        [r for r in rules if r.chain == chain and r.enabled],
        key=lambda r: r.order,
    )

    evaluated_ids: List[str] = []

    for rule in candidate_rules:
        evaluated_ids.append(rule.id)
        if matches_rule(rule, src_ip, dst_ip, packet):
            reason_str = (
                f"Cocok dengan rule ID '{rule.id}' (order {rule.order}) "
                f"pada chain {chain.value.upper()}: action {rule.action.value.upper()}"
            )
            return RuleEvaluationResult(
                action=rule.action,
                matched_rule=rule,
                evaluated_rule_ids=tuple(evaluated_ids),
                reason=reason_str,
            )

    # Jika tidak ada yang cocok, gunakan default policy
    return RuleEvaluationResult(
        action=default_policy,
        matched_rule=None,
        evaluated_rule_ids=tuple(evaluated_ids),
        reason=f"Tidak ada rule cocok pada chain {chain.value.upper()}. Default policy: {default_policy.value.upper()}",
    )
