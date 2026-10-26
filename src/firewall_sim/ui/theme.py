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
    """Return a textual badge for a simulation Decision without emojis.
    The badge includes text and description satisfying accessibility requirements.
    """
    if decision == Decision.ACCEPT:
        return "[ACCEPT] Lolos Kebijakan"
    if decision == Decision.DROP:
        return "[DROP] Ditolak Firewall"
    if decision == Decision.NO_ROUTE:
        return "[NO_ROUTE] Rute Tidak Ditemukan"
    if decision == Decision.INVALID_CONFIG:
        return "[INVALID_CONFIG] Konfigurasi Tidak Valid"
    if decision == Decision.UNSUPPORTED_CASE:
        return "[UNSUPPORTED_CASE] Kasus Belum Didukung"
    return f"[{decision.value}]"


def inject_theme_css() -> str:
    """Return custom CSS rules for .fw-* design system elements.
    Includes smooth micro-transitions and prefers-reduced-motion accessibility.
    Does NOT touch Streamlit internal classes (.st-emotion-cache, [data-testid]).
    """
    return """
    <style>
    /* Firewall Simulator Design System - Cockpit Engineering Styles */
    :root {
        --fw-primary: #3B82F6;
        --fw-primary-hover: #2563EB;
        --fw-surface: #1E293B;
        --fw-border: #334155;
        --fw-muted: #94A3B8;
        --fw-text: #F9FAFB;
        --fw-mono: ui-monospace, 'SF Mono', 'Cascadia Code', 'Fira Code', Menlo, Consolas, monospace;
    }

    /* Workflow Rail */
    .fw-workflow-rail {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.5rem;
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid var(--fw-border);
        border-radius: 0.75rem;
        padding: 0.6rem 1rem;
        margin-bottom: 1.25rem;
        backdrop-filter: blur(8px);
    }

    .fw-step-item {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        font-size: 0.825rem;
        font-weight: 500;
        color: var(--fw-muted);
        padding: 0.25rem 0.5rem;
        border-radius: 0.375rem;
        transition: color 200ms ease, background 200ms ease;
    }

    .fw-step-item.active {
        color: var(--fw-text);
        background: rgba(59, 130, 246, 0.15);
        border: 1px solid rgba(59, 130, 246, 0.4);
        font-weight: 600;
    }

    .fw-step-num {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 1.25rem;
        height: 1.25rem;
        border-radius: 50%;
        font-size: 0.75rem;
        background: rgba(148, 163, 184, 0.2);
        color: var(--fw-text);
    }

    .fw-step-item.active .fw-step-num {
        background: var(--fw-primary);
        color: #FFFFFF;
    }

    .fw-step-arrow {
        color: var(--fw-border);
        font-size: 0.75rem;
    }

    /* Cards and KPI elements */
    .fw-card {
        background: var(--fw-surface);
        border: 1px solid var(--fw-border);
        border-radius: 0.75rem;
        padding: 1rem;
        margin-bottom: 0.75rem;
        transition: border-color 200ms ease, box-shadow 200ms ease;
    }

    .fw-card:hover {
        border-color: rgba(59, 130, 246, 0.5);
    }

    .fw-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        font-family: var(--fw-mono);
        font-size: 0.8rem;
        letter-spacing: 0.02em;
    }

    .fw-code-pill {
        font-family: var(--fw-mono);
        background: rgba(15, 23, 42, 0.8);
        border: 1px solid var(--fw-border);
        padding: 0.1rem 0.4rem;
        border-radius: 0.25rem;
        font-size: 0.825rem;
        color: #93C5FD;
    }

    /* Terminal Console */
    .fw-terminal-window {
        background: #080D1A;
        border: 1px solid #1E293B;
        border-radius: 0.75rem;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
        overflow: hidden;
        margin-bottom: 1rem;
    }

    .fw-terminal-bar {
        background: #0F172A;
        padding: 0.4rem 0.75rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid #1E293B;
        font-family: var(--fw-mono);
        font-size: 0.75rem;
        color: var(--fw-muted);
    }

    .fw-terminal-dots {
        display: flex;
        gap: 0.35rem;
    }

    .fw-terminal-dot {
        width: 0.65rem;
        height: 0.65rem;
        border-radius: 50%;
        display: inline-block;
    }

    .fw-terminal-dot.close { background: #EF4444; }
    .fw-terminal-dot.min { background: #F59E0B; }
    .fw-terminal-dot.max { background: #10B981; }

    .fw-terminal-body {
        padding: 0.85rem 1rem;
        font-family: var(--fw-mono);
        font-size: 0.85rem;
        line-height: 1.5;
        max-height: 380px;
        overflow-y: auto;
    }

    .fw-term-line {
        margin: 0.2rem 0;
        white-space: pre-wrap;
        word-break: break-all;
    }

    .fw-term-prompt {
        color: #38BDF8;
        font-weight: 600;
    }

    .fw-term-cmd {
        color: #F8FAFC;
    }

    .fw-term-ok {
        color: #34D399;
    }

    .fw-term-err {
        color: #F87171;
    }

    .fw-term-dim {
        color: #64748B;
    }

    /* Accessibility: Reduced motion */
    @media (prefers-reduced-motion: reduce) {
        .fw-workflow-rail, .fw-step-item, .fw-card {
            transition: none !important;
            animation: none !important;
        }
    }
    </style>
    """

