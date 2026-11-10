"""Teks yang ramah pembaca untuk data internal (nama perangkat, nomor aturan, kalimat engine)."""

from __future__ import annotations

import re
from typing import Optional

from firewall_sim.core.models import Decision, ProjectState

# Warna LED per keputusan: (kelas CSS, warna LED, warna teks yang lulus kontras)
DECISION_STYLE = {
    Decision.ACCEPT: ("ok", "var(--fw-led-ok)", "var(--fw-ok-text)"),
    Decision.DROP: ("deny", "var(--fw-led-deny)", "var(--fw-deny-text)"),
}
AMBER_STYLE = ("amber", "var(--fw-led-amber)", "var(--fw-amber-text)")


def decision_style(decision: Decision):
    return DECISION_STYLE.get(decision, AMBER_STYLE)


def device_name(state: ProjectState, device_id: Optional[str]) -> str:
    """Nama perangkat; bila tidak ditemukan (mis. alamat IP), tampilkan teks aslinya."""
    dev = state.get_device(device_id) if device_id else None
    return dev.name if dev else (device_id or "-")


def rule_label(state: ProjectState, rule_id: Optional[str]) -> str:
    """'aturan #2, FORWARD', 'kebijakan default', atau 'aturan sudah dihapus'."""
    if not rule_id:
        return "kebijakan default"
    rule = next((r for r in state.rules if r.id == rule_id), None)
    if rule is None:
        return "aturan sudah dihapus"
    return f"aturan #{rule.order}, {rule.chain.value.upper()}"


def friendly_text(state: ProjectState, raw: str) -> str:
    """Teks dari engine tanpa ID internal: "rule ID 'x' (order 2)" menjadi "aturan #2", ID perangkat menjadi nama."""
    text = re.sub(r"rule ID '[^']*' \(order (\d+)\)", r"aturan #\1", raw or "")
    for dev in state.devices:
        text = re.sub(rf"\b{re.escape(dev.id)}\b", dev.name, text)
    return text
