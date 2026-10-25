"""Traffic analytics and log aggregation module.

ATURAN ARSITEKTUR:
- Murni Python standard library (tanpa dependensi Streamlit atau library UI).
- Mengolah pasangan (PacketTest, SimulationResult) menjadi TrafficLogEntry terstruktur.
- Menyediakan filter deterministik dan kalkulasi ringkasan metrik.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from firewall_sim.core.models import (
    Decision,
    PacketTest,
    Protocol,
    SimulationResult,
)


@dataclass(frozen=True)
class TrafficLogEntry:
    id: str
    timestamp: datetime
    source_device: str
    destination_target: str
    protocol: Protocol
    src_port: Optional[int]
    dst_port: Optional[int]
    decision: Decision
    matched_rule_id: Optional[str]
    reason: str
    config_revision: int


def create_log_entry(packet: PacketTest, result: SimulationResult) -> TrafficLogEntry:
    """Membuat entri traffic log dari pasangan PacketTest dan SimulationResult."""
    dst = packet.destination_device_id or packet.destination_ip or "unknown"
    return TrafficLogEntry(
        id=f"log_{result.test_id}",
        timestamp=result.timestamp,
        source_device=packet.source_device_id,
        destination_target=dst,
        protocol=packet.protocol,
        src_port=packet.src_port,
        dst_port=packet.dst_port,
        decision=result.decision,
        matched_rule_id=result.matched_rule_id,
        reason=result.reason,
        config_revision=result.config_revision,
    )


def summarize_traffic(logs: List[TrafficLogEntry]) -> Dict[str, int]:
    """Menghitung agregasi statistik keputusan trafik."""
    summary = {
        "total": len(logs),
        "ACCEPT": 0,
        "DROP": 0,
        "NO_ROUTE": 0,
        "OTHER": 0,
    }
    for item in logs:
        if item.decision == Decision.ACCEPT:
            summary["ACCEPT"] += 1
        elif item.decision == Decision.DROP:
            summary["DROP"] += 1
        elif item.decision == Decision.NO_ROUTE:
            summary["NO_ROUTE"] += 1
        else:
            summary["OTHER"] += 1
    return summary


def filter_traffic(
    logs: List[TrafficLogEntry],
    decision: Optional[Decision] = None,
    ip_or_device: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> List[TrafficLogEntry]:
    """Memfilter entri log berdasarkan keputusan, alamat/device, dan rentang waktu."""
    filtered = []
    term = ip_or_device.strip().lower() if ip_or_device else None

    for item in logs:
        if decision is not None and item.decision != decision:
            continue

        if term:
            src_match = term in item.source_device.lower()
            dst_match = term in item.destination_target.lower()
            if not (src_match or dst_match):
                continue

        if start_time and item.timestamp < start_time:
            continue
        if end_time and item.timestamp > end_time:
            continue

        filtered.append(item)

    return filtered
