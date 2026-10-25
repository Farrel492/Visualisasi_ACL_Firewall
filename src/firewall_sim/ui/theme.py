"""UI theme tokens and badge helpers for Firewall Simulator.

Design system tokens: colors, spacing, typography.
"""

from __future__ import annotations

from firewall_sim.core.models import Decision

# Palet PRD Bagian 11 & Spesifikasi Visual
COLOR_BASE = "#0F172A"
COLOR_SURFACE = "#1E293B"
COLOR_SIDEBAR = "#0B1220"
COLOR_BORDER = "#334155"
COLOR_TEXT = "#F9FAFB"
COLOR_PRIMARY = "#3B82F6"
COLOR_ALLOW = "#16A34A"
COLOR_DENY = "#DC2626"
COLOR_WARNING = "#F59E0B"
COLOR_AMBER = "#F59E0B"
COLOR_MUTED = "#94A3B8"

# Radius tokens
RADIUS_BASE = "0.75rem"
RADIUS_BUTTON = "0.75rem"

# Spacing tokens (rem units) for consistent layout
SPACING_XS = "0.25rem"
SPACING_SM = "0.5rem"
SPACING_MD = "1rem"
SPACING_LG = "1.5rem"
SPACING_XL = "2rem"

# Typography defaults (system font stack via .streamlit/config.toml)
FONT_FAMILY = "sans-serif"
FONT_SIZE_BASE = "1rem"
FONT_SIZE_SM = "0.875rem"
FONT_SIZE_LG = "1.125rem"

def get_decision_badge(decision: Decision) -> str:
    """Return a textual badge with icon for a simulation Decision.
    The badge includes both colour‑semantic icon and description; it does
    not rely on UI colour alone, satisfying accessibility requirements.
    """
    if decision == Decision.ACCEPT:
        return "🟢 ACCEPT (Lolos Kebijakan)"
    if decision == Decision.DROP:
        return "🔴 DROP (Ditolak Firewall)"
    if decision == Decision.NO_ROUTE:
        return "⚠️ NO_ROUTE (Rute Tidak Ditemukan)"
    if decision == Decision.INVALID_CONFIG:
        return "❌ INVALID_CONFIG (Konfigurasi Tidak Valid)"
    if decision == Decision.UNSUPPORTED_CASE:
        return "❓ UNSUPPORTED_CASE (Kasus Belum Didukung)"
    return f"ℹ️ {decision.value}"
