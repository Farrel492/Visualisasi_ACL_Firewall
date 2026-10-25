"""Security alerts and event generator module.

ATURAN ARSITEKTUR:
- Setiap penolakan (DROP) dapat menghasilkan event firewall.
- LARANGAN KETAT AGENTS.md: Jangan menyatakan setiap DROP sebagai serangan (attack).
  Penolakan dapat merupakan perilaku kebijakan filter jaringan yang normal.
- Severity default adalah 'info' (atau 'warning' jika policy highlight aktif).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from firewall_sim.core.models import Decision, SecurityEvent, SimulationResult


@dataclass(frozen=True)
class AlertPolicy:
    highlight_drop: bool = False
    default_severity: str = "info"


def derive_alerts(
    result: SimulationResult,
    policy: Optional[AlertPolicy] = None,
) -> List[SecurityEvent]:
    """Menghasilkan SecurityEvent berdasarkan hasil simulasi paket.

    Hanya hasil DROP yang menghasilkan SecurityEvent bertipe FIREWALL_DROP.
    Hasil ACCEPT, NO_ROUTE, atau INVALID_CONFIG tidak menghasilkan alert keamanan.
    """
    if result.decision != Decision.DROP:
        return []

    pol = policy or AlertPolicy()
    severity = "warning" if pol.highlight_drop else pol.default_severity

    # Ambil device terakhir dari trace (tempat paket di-drop)
    drop_device_id = None
    if result.trace:
        drop_device_id = result.trace[-1].device_id

    event_id = f"evt_{result.test_id}_{int(result.timestamp.timestamp() * 1000)}"

    msg = (
        f"Paket di-DROP oleh kebijakan firewall pada perangkat '{drop_device_id or 'unknown'}'. "
        f"Alasan: {result.reason}"
    )

    event = SecurityEvent(
        id=event_id,
        test_id=result.test_id,
        event_type="FIREWALL_DROP",
        severity=severity,
        timestamp=result.timestamp,
        message=msg,
        device_id=drop_device_id,
        rule_id=result.matched_rule_id,
        acknowledged=False,
    )
    return [event]
